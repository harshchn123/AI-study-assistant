# AI Study Assistant using RAG

A Streamlit final-year project that lets students upload PDF study material and chat with it using Retrieval-Augmented Generation.

## Features

- Upload PDF notes, textbooks, research papers, and lecture notes.
- Extract PDF text with PyPDF.
- Extract scanned PDF text with Gemini OCR fallback.
- Split text into chunks with LangChain.
- Store chunks in a fast local SQLite index for quick demos.
- Optionally generate embeddings with Sentence Transformers and ChromaDB for semantic search.
- Answer questions only from uploaded document context.
- Generate chapter summaries, MCQs, viva questions, and short revision notes.
- Run an interactive quiz with answer checking, explanations, and final score.
- Supports Gemini, OpenAI, and OpenRouter through environment variables.

## Project Structure

```text
ai-study-assistant/
|-- app.py
|-- uploads/
|-- chroma_db/
|-- utils/
|   |-- pdf_loader.py
|   |-- embeddings.py
|   |-- retriever.py
|   `-- chatbot.py
|-- .env
|-- requirements.txt
`-- README.md
```

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Add an API key in `.env`.

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_OCR_MODEL=gemini-flash-latest
```

You can also set `LLM_PROVIDER=openai` or `LLM_PROVIDER=openrouter` and fill the matching API key.

4. Run the app.

```bash
streamlit run app.py
```

## Production Demo Settings

For a fast professor demo, use:

```env
OCR_PROVIDER=gemini
RETRIEVAL_MODE=keyword
SEMANTIC_INDEX_ON_PROCESS=false
```

This stores document chunks in a fast local SQLite index. ChromaDB and SentenceTransformer embeddings are used only when **Build semantic index** is enabled.

For Streamlit Cloud, copy values from `.streamlit/secrets.toml.example` into the app secrets panel. Do not upload `.env`.

## Workflow

1. Upload one or more PDF files in the sidebar.
2. Click **Process PDF**.
3. The app extracts selectable text. For scanned pages, enable **OCR scanned pages** so Gemini can extract text from images.
4. The app chunks text, embeds chunks, and stores them in ChromaDB.
5. Choose a specific PDF from **Answer from** to avoid mixing answers from older uploads.
6. Keep **Retrieval mode** on **keyword (fast)** for quicker responses, or switch to semantic mode for vague conceptual questions.
7. Ask questions in the chat interface.
8. Use the exam tools to generate summaries, MCQs, viva questions, revision notes, or an interactive quiz.

## Scanned PDF Notes

- Scanned PDFs require **OCR scanned pages** and a valid Gemini API key.
- For notebook/photo PDFs, set **OCR type** to **Handwritten notes** and keep **Force OCR all pages** enabled before processing.
- OCR results are cached per PDF page after successful extraction, so reprocessing the same file is faster.
- If a PDF gives unrelated answers, select that exact file in **Answer from** or clear the vector database and reprocess only the needed PDF.
- Keep **Build semantic index** off for production demos unless you specifically need semantic search. This avoids slow embedding generation during PDF processing.

## Notes for Viva or Report

This project uses RAG to reduce hallucination. The uploaded PDFs are converted into chunks and stored in a local index. The retriever selects relevant chunks for a user query, and the LLM receives only the retrieved context plus the student question, so answers stay grounded in the uploaded material. Semantic vector search with ChromaDB can be enabled when needed.

## Future Enhancements

- Voice assistant.
- Student login.
- Persistent chat history.
- Exam preparation dashboard.
- Personalized learning recommendations.
