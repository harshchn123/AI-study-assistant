import os
from typing import Any

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

from chromadb import EmbeddingFunction
from chromadb.api.types import Documents, Embeddings


class SentenceTransformerEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Any | None = None

    def __call__(self, input: Documents) -> Embeddings:
        if self._model is None:
            self._model = self._load_model()

        vectors = self._model.encode(
            list(input),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def _load_model(self) -> Any:
        from sentence_transformers import SentenceTransformer

        try:
            return SentenceTransformer(self.model_name, local_files_only=True)
        except Exception as exc:
            if os.getenv("ALLOW_EMBEDDING_DOWNLOAD", "false").lower() == "true":
                return SentenceTransformer(self.model_name)

            raise RuntimeError(
                "Embedding model is not fully available offline. Run once with "
                "ALLOW_EMBEDDING_DOWNLOAD=true in .env, or connect to the internet "
                "and restart the app so SentenceTransformers can finish caching "
                f"{self.model_name}."
            ) from exc
