import hashlib
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from utils.pdf_loader import extract_pdf_pages


@dataclass(frozen=True)
class ProcessedPdf:
    filename: str
    pages: int
    chunks: int
    ocr_pages: int = 0
    semantic_indexed: bool = False


@dataclass(frozen=True)
class RetrievedContext:
    context: str
    sources: list[dict]


class StudyVectorStore:
    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "study_materials",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.sqlite_path = self.persist_directory / "study_chunks.sqlite3"
        self._chroma_client = None
        self._chroma_collection = None
        self._init_sqlite()

    def add_pdf(
        self,
        pdf_path: Path,
        use_ocr: bool = True,
        ocr_mode: str = "printed",
        force_ocr: bool = False,
        build_semantic_index: bool | None = None,
    ) -> ProcessedPdf:
        pages = extract_pdf_pages(
            pdf_path,
            use_ocr=use_ocr,
            ocr_mode=ocr_mode,
            force_ocr=force_ocr,
        )
        if not pages:
            raise ValueError(f"No extractable text found in {pdf_path.name}.")

        rows: list[tuple[str, str, int, int, str, str]] = []
        for page in pages:
            chunks = self._split_text(page.text)
            for chunk_index, chunk in enumerate(chunks):
                chunk_id = self._chunk_id(pdf_path.name, page.page_number, chunk_index, chunk)
                rows.append(
                    (
                        chunk_id,
                        pdf_path.name,
                        page.page_number,
                        chunk_index,
                        page.extraction_method,
                        chunk,
                    )
                )

        with self._connect() as connection:
            connection.execute("DELETE FROM chunks WHERE source = ?", (pdf_path.name,))
            connection.executemany(
                """
                INSERT OR REPLACE INTO chunks
                    (id, source, page, chunk_index, method, text)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

        semantic_indexed = False
        should_build_semantic = (
            build_semantic_index
            if build_semantic_index is not None
            else os.getenv("SEMANTIC_INDEX_ON_PROCESS", "false").lower() == "true"
        )
        if should_build_semantic:
            self._upsert_semantic(rows, source=pdf_path.name)
            semantic_indexed = True

        ocr_pages = sum(1 for page in pages if page.extraction_method == "ocr")
        return ProcessedPdf(
            filename=pdf_path.name,
            pages=len(pages),
            chunks=len(rows),
            ocr_pages=ocr_pages,
            semantic_indexed=semantic_indexed,
        )

    def retrieve(
        self,
        query: str,
        k: int = 4,
        source: str | None = None,
        mode: str = "keyword",
    ) -> RetrievedContext:
        if not self.has_documents():
            return RetrievedContext(context="", sources=[])

        if mode == "semantic":
            try:
                return self._semantic_retrieve(query=query, k=k, source=source)
            except Exception:
                return self._keyword_retrieve(query=query, k=k, source=source)

        return self._keyword_retrieve(query=query, k=k, source=source)

    def representative_context(
        self,
        max_chunks: int = 20,
        source: str | None = None,
    ) -> RetrievedContext:
        rows = self._fetch_rows(source=source, limit=max_chunks)
        return self._rows_to_context(rows)

    def has_documents(self) -> bool:
        return self.document_count() > 0

    def document_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()
        return int(row[0] if row else 0)

    def list_sources(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT source FROM chunks ORDER BY source"
            ).fetchall()
        return [row[0] for row in rows]

    def reset(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM chunks")

        self._delete_semantic_collection()

    def _keyword_retrieve(
        self,
        query: str,
        k: int = 4,
        source: str | None = None,
    ) -> RetrievedContext:
        rows = self._fetch_rows(source=source)
        if not rows:
            return RetrievedContext(context="", sources=[])

        query_terms = self._important_terms(query)
        scored = [
            (self._keyword_score(row["text"], query_terms, query), row)
            for row in rows
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        top_rows = [row for _, row in scored[: min(k, len(scored))]]
        return self._rows_to_context(top_rows)

    def _semantic_retrieve(
        self,
        query: str,
        k: int = 4,
        source: str | None = None,
    ) -> RetrievedContext:
        collection = self._get_chroma_collection()
        count = self._source_count(source) if source else self.document_count()
        if count == 0:
            return RetrievedContext(context="", sources=[])

        query_terms = self._important_terms(query)
        max_distance = self._float_env("SEMANTIC_MAX_DISTANCE", 0.85)
        candidate_count = min(max(k * 4, 12), count)
        allowed_sources = {source} if source else set(self.list_sources())
        results = collection.query(
            query_texts=[query],
            n_results=candidate_count,
            where={"source": source} if source else None,
            include=["documents", "metadatas", "distances"],
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        candidates = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            result_source = metadata.get("source", "Unknown file")
            if allowed_sources and result_source not in allowed_sources:
                continue

            keyword_score = self._keyword_score(document, query_terms, query)
            distance_value = float(distance)
            if distance_value > max_distance and keyword_score <= 0:
                continue

            candidates.append(
                (
                    distance_value - min(keyword_score, 8) * 0.03,
                    {
                        "source": result_source,
                        "page": metadata.get("page", "N/A"),
                        "method": metadata.get("method", "text"),
                        "text": document,
                        "distance": round(distance_value, 4),
                    },
                )
            )

        if not candidates:
            keyword_result = self._keyword_retrieve(query=query, k=k, source=source)
            if keyword_result.sources and any(
                self._keyword_score(item.get("preview", ""), query_terms, query) > 0
                for item in keyword_result.sources
            ):
                return keyword_result
            return RetrievedContext(context="", sources=[])

        candidates.sort(key=lambda item: item[0])
        rows = [row for _, row in candidates[: min(k, len(candidates))]]
        return self._rows_to_context(rows)

    @staticmethod
    def _float_env(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except ValueError:
            return default

    def _upsert_semantic(
        self,
        rows: list[tuple[str, str, int, int, str, str]],
        source: str,
    ) -> None:
        collection = self._get_chroma_collection()
        try:
            collection.delete(where={"source": source})
        except Exception:
            pass

        collection.upsert(
            ids=[row[0] for row in rows],
            documents=[row[5] for row in rows],
            metadatas=[
                {
                    "source": row[1],
                    "page": row[2],
                    "chunk_index": row[3],
                    "method": row[4],
                }
                for row in rows
            ],
        )

    def _get_chroma_collection(self):
        if self._chroma_collection is not None:
            return self._chroma_collection

        import chromadb
        from utils.embeddings import SentenceTransformerEmbeddingFunction

        self._chroma_client = chromadb.PersistentClient(path=str(self.persist_directory))
        self._chroma_collection = self._chroma_client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=SentenceTransformerEmbeddingFunction(self.embedding_model),
            metadata={"hnsw:space": "cosine"},
        )
        return self._chroma_collection

    def _delete_semantic_collection(self) -> None:
        try:
            if self._chroma_client is None:
                import chromadb

                self._chroma_client = chromadb.PersistentClient(
                    path=str(self.persist_directory)
                )
            self._chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass
        finally:
            self._chroma_collection = None

    def _init_sqlite(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    method TEXT NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _fetch_rows(
        self,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        query = "SELECT source, page, method, text FROM chunks"
        params: list[object] = []
        if source:
            query += " WHERE source = ?"
            params.append(source)
        query += " ORDER BY source, page, chunk_index"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def _source_count(self, source: str | None) -> int:
        if not source:
            return self.document_count()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM chunks WHERE source = ?",
                (source,),
            ).fetchone()
        return int(row[0] if row else 0)

    def _rows_to_context(self, rows: list[dict]) -> RetrievedContext:
        context_parts: list[str] = []
        sources: list[dict] = []
        for row in rows:
            source = row.get("source", "Unknown file")
            page = row.get("page", "N/A")
            text = row.get("text", "")
            context_parts.append(f"[Source: {source}, page {page}]\n{text}")
            sources.append(
                {
                    "source": source,
                    "page": page,
                    "method": row.get("method", "text"),
                    "preview": text[:300],
                }
            )

        return RetrievedContext(context="\n\n".join(context_parts), sources=sources)

    @staticmethod
    def _split_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
        cleaned = " ".join(text.split())
        if not cleaned:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(start + chunk_size, len(cleaned))
            if end < len(cleaned):
                boundary = max(
                    cleaned.rfind(". ", start, end),
                    cleaned.rfind(" ", start, end),
                )
                if boundary > start + int(chunk_size * 0.6):
                    end = boundary + 1
            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(cleaned):
                break
            start = max(end - overlap, start + 1)
        return chunks

    @staticmethod
    def _important_terms(text: str) -> list[str]:
        stopwords = {
            "the",
            "and",
            "for",
            "from",
            "this",
            "that",
            "what",
            "when",
            "where",
            "which",
            "with",
            "about",
            "into",
            "give",
            "tell",
            "please",
            "explain",
            "summary",
            "summarize",
        }
        terms = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return [term for term in terms if len(term) > 2 and term not in stopwords]

    @staticmethod
    def _keyword_score(document: str, query_terms: list[str], raw_query: str) -> float:
        lowered = document.lower()
        if not query_terms:
            return 0

        score = 0.0
        for term in set(query_terms):
            score += lowered.count(term)

        phrase = " ".join(query_terms)
        if phrase and phrase in lowered:
            score += 5

        raw = raw_query.strip().lower()
        if raw and raw in lowered:
            score += 8

        return score

    @staticmethod
    def _chunk_id(filename: str, page: int, chunk_index: int, chunk: str) -> str:
        raw = f"{filename}:{page}:{chunk_index}:{chunk}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
