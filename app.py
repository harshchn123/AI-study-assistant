import os
import html
import json
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from utils.chatbot import MissingApiKeyError, StudyAssistantLLM
from utils.pdf_loader import save_uploaded_file
from utils.retriever import StudyVectorStore


load_dotenv()

APP_ROOT = Path(__file__).parent
UPLOAD_DIR = APP_ROOT / "uploads"
CHROMA_DIR = APP_ROOT / "chroma_db"
SUPPORTED_LLM_PROVIDERS = {"gemini", "openrouter", "openai"}
TOOL_TABS = [
    ("chat", "💬", "Chat"),
    ("summary", "📄", "Summary"),
    ("mcqs", "☰", "MCQs"),
    ("quiz", "❔", "Quiz"),
    ("viva", "🎓", "Viva"),
    ("notes", "📝", "Notes"),
]


def get_default_llm_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    return provider if provider in SUPPORTED_LLM_PROVIDERS else "gemini"


def get_default_top_k() -> int:
    try:
        value = int(os.getenv("RETRIEVAL_TOP_K", "4"))
    except ValueError:
        value = 4
    return max(2, min(value, 8))


def get_default_retrieval_mode() -> str:
    mode = os.getenv("RETRIEVAL_MODE", "keyword").lower().strip()
    return "semantic" if mode == "semantic" else "keyword"


st.set_page_config(
    page_title="AI Study Assistant",
    page_icon=":books:",
    layout="wide",
)


def apply_app_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #0d1117;
            --panel: #111822;
            --panel-soft: #151d28;
            --line: #334155;
            --muted: #a7b0c0;
            --text: #f8fafc;
            --accent: #ff4b4b;
            --green: #42d66b;
            --blue: #60a5fa;
        }

        .stApp {
            background:
                radial-gradient(circle at 70% 5%, rgba(36, 57, 91, 0.22), transparent 34%),
                linear-gradient(135deg, #0b1017 0%, #0d1117 52%, #080c12 100%);
            color: var(--text);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #121a24 0%, #0f1620 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.22);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding: 2rem 1.25rem;
        }

        [data-testid="stSidebar"] h1 {
            font-size: 1.2rem;
            margin-bottom: 0.25rem;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: rgba(15, 23, 42, 0.88);
            border: 1px dashed rgba(148, 163, 184, 0.38);
            border-radius: 8px;
            padding: 1.2rem 0.8rem;
        }

        .block-container {
            max-width: 1240px;
            padding-top: 2.25rem;
            padding-left: 3.5rem;
            padding-right: 3rem;
        }

        h1 {
            font-size: 2.6rem !important;
            letter-spacing: 0 !important;
            margin-bottom: 0.85rem !important;
        }

        h2, h3 {
            letter-spacing: 0 !important;
        }

        div[data-testid="stTextInput"] input {
            min-height: 3.2rem;
            border-radius: 8px;
            border: 1px solid rgba(148, 163, 184, 0.34);
            background: rgba(17, 24, 39, 0.82);
        }

        div[data-testid="stButton"] > button {
            border-radius: 8px;
            min-height: 2.75rem;
            font-weight: 700;
        }

        .tool-nav {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0;
            border-bottom: 1px solid rgba(148, 163, 184, 0.28);
            margin-top: 0.45rem;
            height: 3.15rem;
            align-items: stretch;
        }

        .tool-tab {
            width: 100%;
            height: 3.15rem;
            padding: 0 1rem;
            color: #cbd5e1;
            font-weight: 700;
            border-bottom: 3px solid transparent;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.45rem;
            text-decoration: none !important;
            font-size: 1rem;
        }

        .tool-tab:hover {
            color: #ffffff;
            background: rgba(148, 163, 184, 0.06);
            text-decoration: none !important;
        }

        .tool-tab.active {
            color: var(--accent) !important;
            border-bottom-color: var(--accent);
        }

        .tool-tab-content {
            padding-top: 1rem;
        }

        .mcq-card {
            border: 1px solid rgba(148, 163, 184, 0.34);
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.74), rgba(11, 18, 29, 0.9));
            border-radius: 8px;
            padding: 1.05rem 1.25rem;
            margin: 0 0 0.9rem 0;
        }

        .viva-card {
            border: 1px solid rgba(148, 163, 184, 0.34);
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.74), rgba(11, 18, 29, 0.9));
            border-radius: 8px;
            padding: 1rem 1.2rem;
            margin: 0 0 0.9rem 0;
        }

        .viva-section {
            color: #f8fafc;
            font-size: 1.1rem;
            font-weight: 800;
            margin: 1rem 0 0.55rem 0;
        }

        .mcq-header {
            display: grid;
            grid-template-columns: 2.4rem 1fr;
            gap: 0.9rem;
            align-items: start;
            margin-bottom: 0.85rem;
        }

        .mcq-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2rem;
            height: 2rem;
            border-radius: 6px;
            background: linear-gradient(135deg, #ff4b4b, #92343f);
            color: white;
            font-weight: 800;
        }

        .viva-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2rem;
            height: 2rem;
            border-radius: 6px;
            background: linear-gradient(135deg, #ff4b4b, #92343f);
            color: white;
            font-weight: 800;
            margin-right: 0.8rem;
            vertical-align: top;
        }

        .mcq-question {
            color: #f8fafc;
            font-size: 1.02rem;
            font-weight: 800;
            line-height: 1.45;
            padding-top: 0.15rem;
        }

        .viva-question {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.45;
            display: inline-block;
            width: calc(100% - 3rem);
        }

        .viva-answer {
            margin-left: 3rem;
            margin-top: 0.6rem;
            border-radius: 6px;
            padding: 0.58rem 0.75rem;
            background: rgba(30, 64, 175, 0.22);
            border: 1px solid rgba(96, 165, 250, 0.28);
            color: #dbeafe;
            line-height: 1.45;
        }

        .mcq-options {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.55rem 1.4rem;
            margin-left: 3.3rem;
            margin-bottom: 0.85rem;
        }

        .mcq-option {
            color: #e5e7eb;
            line-height: 1.45;
        }

        .mcq-answer,
        .mcq-explanation {
            margin-left: 3.3rem;
            border-radius: 6px;
            padding: 0.58rem 0.75rem;
            margin-top: 0.45rem;
            line-height: 1.45;
        }

        .mcq-answer {
            background: rgba(22, 101, 52, 0.28);
            border: 1px solid rgba(34, 197, 94, 0.28);
            color: #bbf7d0;
        }

        .mcq-explanation {
            background: rgba(30, 64, 175, 0.22);
            border: 1px solid rgba(96, 165, 250, 0.28);
            color: #dbeafe;
        }

        .quiz-card {
            border: 1px solid rgba(148, 163, 184, 0.34);
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.78), rgba(11, 18, 29, 0.92));
            border-radius: 8px;
            padding: 1.2rem 1.3rem;
            margin: 0.8rem 0 1rem 0;
        }

        .quiz-topline {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            color: #cbd5e1;
            font-weight: 700;
            margin-bottom: 0.9rem;
        }

        .quiz-score {
            color: #ffb4b4;
        }

        .quiz-question {
            color: #f8fafc;
            font-size: 1.12rem;
            font-weight: 800;
            line-height: 1.5;
            margin-bottom: 0.8rem;
        }

        .quiz-feedback-correct,
        .quiz-feedback-wrong {
            border-radius: 6px;
            padding: 0.6rem 0.75rem;
            margin-top: 0.7rem;
            font-weight: 700;
        }

        .quiz-feedback-correct {
            background: rgba(22, 101, 52, 0.28);
            border: 1px solid rgba(34, 197, 94, 0.28);
            color: #bbf7d0;
        }

        .quiz-feedback-wrong {
            background: rgba(127, 29, 29, 0.28);
            border: 1px solid rgba(248, 113, 113, 0.28);
            color: #fecaca;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .tool-nav {
                grid-template-columns: repeat(3, minmax(0, 1fr));
                height: auto;
            }

            .tool-tab {
                height: 2.8rem;
                font-size: 0.92rem;
            }

            .mcq-options {
                grid-template-columns: 1fr;
                margin-left: 0;
            }

            .mcq-answer,
            .mcq-explanation,
            .viva-answer {
                margin-left: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_streamlit_secrets() -> None:
    try:
        for key, value in st.secrets.items():
            os.environ.setdefault(str(key), str(value))
    except Exception:
        pass


apply_streamlit_secrets()
apply_app_style()


@st.cache_resource(show_spinner=False)
def get_vector_store(cache_version: str) -> StudyVectorStore:
    return StudyVectorStore(persist_directory=str(CHROMA_DIR))


def reset_chat() -> None:
    st.session_state.messages = []
    st.session_state.exam_output = None


def reset_quiz() -> None:
    st.session_state.quiz = {
        "questions": [],
        "current": 0,
        "answers": {},
        "score": 0,
        "submitted": {},
        "sources": [],
    }


def select_exam_tool(action: str) -> None:
    st.session_state.selected_exam_tool = action
    st.session_state.pending_exam_action = action


def submit_question() -> None:
    question = st.session_state.get("question_input", "").strip()
    if question:
        st.session_state.pending_question = question
        st.session_state.question_input = ""


def get_active_tab() -> str:
    raw_tab = st.query_params.get("tab", "chat")
    if isinstance(raw_tab, list):
        raw_tab = raw_tab[0] if raw_tab else "chat"
    tab = str(raw_tab).lower().strip()
    valid_tabs = {tab_id for tab_id, _icon, _label in TOOL_TABS}
    return tab if tab in valid_tabs else "chat"


def render_tool_nav(active_tab: str) -> None:
    links = []
    for tab_id, icon, label in TOOL_TABS:
        active_class = " active" if tab_id == active_tab else ""
        links.append(
            f'<a class="tool-tab{active_class}" href="?tab={tab_id}" target="_self">'
            f'<span>{html.escape(icon)}</span><span>{html.escape(label)}</span></a>'
        )
    st.markdown(
        f'<nav class="tool-nav">{"".join(links)}</nav>',
        unsafe_allow_html=True,
    )


def parse_quiz_questions(raw_output: str) -> list[dict]:
    cleaned = raw_output.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("Quiz response was not a JSON list.")

    questions: list[dict] = []
    for index, item in enumerate(data, start=1):
        question = str(item.get("question", "")).strip()
        options = item.get("options", {})
        answer = str(item.get("answer", "")).strip().upper()
        explanation = str(item.get("explanation", "")).strip()

        if isinstance(options, list):
            labels = ["A", "B", "C", "D"]
            options = {
                labels[position]: str(option)
                for position, option in enumerate(options[:4])
            }

        normalized_options = {
            label: str(options.get(label, "")).strip()
            for label in ["A", "B", "C", "D"]
        }

        if not question or answer not in normalized_options:
            raise ValueError(f"Question {index} has invalid quiz format.")
        if any(not value for value in normalized_options.values()):
            raise ValueError(f"Question {index} is missing one or more options.")

        questions.append(
            {
                "question": question,
                "options": normalized_options,
                "answer": answer,
                "explanation": explanation,
            }
        )

    return questions


def split_mcq_blocks(raw_output: str) -> list[str]:
    cleaned = raw_output.strip()
    if not cleaned:
        return []

    cleaned = re.sub(r"\s+(Q\d+\.)", r"\n\1", cleaned)
    cleaned = re.sub(r"\s+([A-D]\.)\s+", r"\n\1 ", cleaned)
    cleaned = re.sub(r"\s+(Answer:)", r"\n\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+(Explanation:)", r"\n\1", cleaned, flags=re.IGNORECASE)

    matches = list(
        re.finditer(
            r"(?ms)(^|\n)(Q\d+\.\s.*?)(?=\nQ\d+\.\s|\Z)",
            cleaned,
        )
    )
    return [match.group(2).strip() for match in matches]


def render_mcq_cards(raw_output: str) -> None:
    blocks = split_mcq_blocks(raw_output)
    if not blocks:
        st.markdown(raw_output)
        return

    for index, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        question = re.sub(r"^Q\d+\.\s*", "", lines[0]).strip()
        options = [line for line in lines[1:] if re.match(r"^[A-D]\.\s+", line)]
        answer_lines = [line for line in lines[1:] if line.lower().startswith("answer:")]
        explanation_lines = [
            line for line in lines[1:] if line.lower().startswith("explanation:")
        ]
        options_html = "\n".join(
            f'<div class="mcq-option">{html.escape(option)}</div>'
            for option in options
        )
        answer_html = (
            f'<div class="mcq-answer"><strong>{html.escape(answer_lines[0])}</strong></div>'
            if answer_lines
            else ""
        )
        explanation_html = (
            f'<div class="mcq-explanation">{html.escape(explanation_lines[0])}</div>'
            if explanation_lines
            else ""
        )

        st.markdown(
            f"""
            <div class="mcq-card">
                <div class="mcq-header">
                    <div class="mcq-number">{index}</div>
                    <div class="mcq-question">{html.escape(question)}</div>
                </div>
                <div class="mcq-options">{options_html}</div>
                {answer_html}
                {explanation_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_viva_cards(raw_output: str) -> None:
    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if not lines:
        st.markdown(raw_output)
        return

    question_count = 0
    active_question: str | None = None
    active_answer: list[str] = []

    def flush_question() -> None:
        if not active_question:
            return
        answer_html = ""
        if active_answer:
            answer_text = " ".join(active_answer).strip()
            answer_html = (
                f'<div class="viva-answer">{html.escape(answer_text)}</div>'
            )
        st.markdown(
            f"""
            <div class="viva-card">
                <span class="viva-number">{question_count}</span>
                <span class="viva-question">{html.escape(active_question)}</span>
                {answer_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for line in lines:
        normalized = re.sub(r"^#+\s*", "", line).strip()
        normalized = normalized.strip("*")
        is_section = (
            "?" not in normalized
            and len(normalized.split()) <= 5
            and any(
                word in normalized.lower()
                for word in ["basic", "intermediate", "advanced", "difficulty"]
            )
        )
        if is_section:
            flush_question()
            active_question = None
            active_answer = []
            st.markdown(
                f'<div class="viva-section">{html.escape(normalized)}</div>',
                unsafe_allow_html=True,
            )
            continue

        question_match = re.match(
            r"^(?:[-*]\s*)?(?:Q?\d+[.)]\s*)?(.*?\?)\s*(.*)$",
            normalized,
            flags=re.IGNORECASE,
        )
        if question_match:
            flush_question()
            question_count += 1
            active_question = question_match.group(1).strip()
            trailing = question_match.group(2).strip()
            active_answer = [trailing] if trailing else []
            continue

        if active_question:
            active_answer.append(normalized)
        else:
            st.markdown(normalized)

    flush_question()

    if question_count == 0:
        st.markdown(raw_output)


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return

    with st.expander("Retrieved sources"):
        for index, source in enumerate(sources, start=1):
            filename = source.get("source", "Unknown file")
            page = source.get("page", "N/A")
            method = source.get("method", "text")
            method_label = " OCR" if method == "ocr" else ""
            st.markdown(f"**{index}. {filename} - Page {page}{method_label}**")
            preview = source.get("preview", "").strip()
            if preview:
                st.caption(preview)


def require_documents(vector_store: StudyVectorStore) -> bool:
    if vector_store.has_documents():
        return True

    st.warning("Upload and process at least one PDF first.")
    return False


def has_retrieved_context(context: str) -> bool:
    return bool(context and len(context.strip()) >= 80)


def insufficient_context_message() -> str:
    return (
        "I could not find enough relevant information in the uploaded document "
        "to answer this accurately. Try selecting the correct PDF, processing the "
        "PDF again with semantic index enabled, or asking with terms used in the notes."
    )


def render_quiz_panel() -> None:
    quiz = st.session_state.quiz
    questions = quiz.get("questions", [])
    if not questions:
        return

    total = len(questions)
    current = int(quiz.get("current", 0))
    current = min(current, total - 1)
    question = questions[current]
    submitted = quiz["submitted"].get(current, False)

    st.markdown(
        f"""
        <div class="quiz-card">
            <div class="quiz-topline">
                <span>Question {current + 1} of {total}</span>
                <span class="quiz-score">Score: {quiz['score']} / {total}</span>
            </div>
            <div class="quiz-question">{html.escape(question['question'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress((current + 1) / total)

    option_labels = [
        f"{label}. {text}"
        for label, text in question["options"].items()
    ]
    selected = st.radio(
        "Choose your answer",
        option_labels,
        key=f"quiz_choice_{current}",
        disabled=submitted,
    )

    selected_label = selected.split(".", 1)[0]

    col_submit, col_next, col_reset = st.columns(3)
    with col_submit:
        if st.button("Submit Answer", disabled=submitted, use_container_width=True):
            quiz["answers"][current] = selected_label
            quiz["submitted"][current] = True
            if selected_label == question["answer"]:
                quiz["score"] += 1
            st.rerun()

    if submitted:
        chosen = quiz["answers"].get(current)
        correct = question["answer"]
        if chosen == correct:
            st.markdown(
                f'<div class="quiz-feedback-correct">Correct. Answer: {html.escape(correct)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="quiz-feedback-wrong">Wrong. Correct answer: {html.escape(correct)}</div>',
                unsafe_allow_html=True,
            )
        if question.get("explanation"):
            st.info(question["explanation"])

    with col_next:
        next_disabled = not submitted or current >= total - 1
        if st.button("Next", disabled=next_disabled, use_container_width=True):
            quiz["current"] = current + 1
            st.rerun()

    with col_reset:
        if st.button("Reset Quiz", use_container_width=True):
            reset_quiz()
            st.rerun()

    if submitted and current == total - 1:
        percentage = round((quiz["score"] / total) * 100, 1)
        st.success(f"Quiz completed. Final score: {quiz['score']} / {total} ({percentage}%).")
        with st.expander("Review answers"):
            for index, item in enumerate(questions):
                chosen = quiz["answers"].get(index, "Not answered")
                st.markdown(
                    f"**Q{index + 1}. {item['question']}**\n\n"
                    f"Your answer: `{chosen}` | Correct answer: `{item['answer']}`"
                )
                if item.get("explanation"):
                    st.caption(item["explanation"])

    render_sources(quiz.get("sources", []))


vector_store = get_vector_store("fast-index-v1")
selected_provider = get_default_llm_provider()
top_k = get_default_top_k()
retrieval_mode = get_default_retrieval_mode()

if "messages" not in st.session_state:
    reset_chat()

if "quiz" not in st.session_state:
    reset_quiz()

with st.sidebar:
    st.title("AI Study Assistant")
    st.caption("Upload PDFs, process them, then ask exam-focused questions.")

    uploaded_files = st.file_uploader(
        "Upload study PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )
    st.caption("Upload your study material to get started.")

    use_ocr = st.checkbox(
        "OCR scanned pages",
        value=True,
        help="Uses Gemini to extract text from PDF pages that do not contain selectable text.",
    )
    st.caption("Process scanned PDFs to extract text.")
    ocr_mode_label = st.selectbox(
        "OCR type",
        ["Printed scan", "Handwritten notes"],
        help="Choose handwritten notes for photo/scanned notebook pages.",
    )
    st.caption("Choose how OCR should be performed.")
    ocr_mode = "handwritten" if ocr_mode_label == "Handwritten notes" else "printed"
    force_ocr = st.checkbox(
        "Force OCR all pages",
        value=ocr_mode == "handwritten",
        help="Use this for handwritten/photo PDFs where PyPDF only extracts page numbers or garbage text.",
    )
    indexed_sources = vector_store.list_sources()
    selected_source = st.selectbox(
        "Answer from",
        ["All indexed PDFs", *indexed_sources],
        help="Choose one PDF to avoid retrieving answers from older uploaded files.",
    )
    st.caption("Select the source for answers.")
    active_source = None if selected_source == "All indexed PDFs" else selected_source
    build_semantic_index = (
        retrieval_mode == "semantic"
        or os.getenv("SEMANTIC_INDEX_ON_PROCESS", "false").lower() == "true"
    )

    process_clicked = st.button("Process PDF", type="primary", use_container_width=True)

    if process_clicked:
        if not uploaded_files:
            st.error("Choose at least one PDF before processing.")
        else:
            with st.spinner("Extracting text and building the fast local index..."):
                processed = []
                for uploaded_file in uploaded_files:
                    try:
                        saved_path = save_uploaded_file(uploaded_file, UPLOAD_DIR)
                        result = vector_store.add_pdf(
                            saved_path,
                            use_ocr=use_ocr,
                            ocr_mode=ocr_mode,
                            force_ocr=force_ocr,
                            build_semantic_index=build_semantic_index,
                        )
                        processed.append(result)
                    except Exception as exc:
                        st.error(f"Could not process {uploaded_file.name}: {exc}")

            if processed:
                st.toast("PDF processed successfully.")
            reset_chat()

    st.divider()

    if st.button("Clear chat", use_container_width=True):
        reset_chat()
        st.rerun()

    if st.button("Reset vector database", use_container_width=True):
        vector_store.reset()
        reset_chat()
        st.success("Document index cleared.")
        st.rerun()


st.title("AI Study Assistant using RAG")

st.subheader("Chat with your PDF")
question_col, send_col = st.columns([12, 1])
with question_col:
    st.text_input(
        "Question",
        placeholder="Ask a question from the uploaded PDF...",
        label_visibility="collapsed",
        key="question_input",
        on_change=submit_question,
    )
with send_col:
    st.button("↑", use_container_width=True, on_click=submit_question)

summary_topic = "Summarize the document"
selected_tool = st.session_state.get("selected_exam_tool")
mcq_count = 10
quiz_count = 5
active_tab = get_active_tab()
render_tool_nav(active_tab)
st.markdown('<div class="tool-tab-content">', unsafe_allow_html=True)

if active_tab == "summary":
    st.button(
        "Generate Summary",
        type="primary" if selected_tool == "summary" else "secondary",
        use_container_width=True,
        on_click=select_exam_tool,
        args=("summary",),
    )

elif active_tab == "mcqs":
    mcq_count = st.number_input("MCQ count", min_value=3, max_value=25, value=10, step=1)
    st.button(
        "Generate MCQs",
        type="primary" if selected_tool == "mcqs" else "secondary",
        use_container_width=True,
        on_click=select_exam_tool,
        args=("mcqs",),
    )

elif active_tab == "quiz":
    quiz_count = st.number_input("Quiz questions", min_value=3, max_value=15, value=5, step=1)
    st.button(
        "Start Interactive Quiz",
        type="primary" if selected_tool == "quiz" else "secondary",
        use_container_width=True,
        on_click=select_exam_tool,
        args=("quiz",),
    )

elif active_tab == "viva":
    st.button(
        "Generate Viva Questions",
        type="primary" if selected_tool == "viva" else "secondary",
        use_container_width=True,
        on_click=select_exam_tool,
        args=("viva",),
    )

elif active_tab == "notes":
    st.button(
        "Generate Notes",
        type="primary" if selected_tool == "notes" else "secondary",
        use_container_width=True,
        on_click=select_exam_tool,
        args=("notes",),
    )

action = st.session_state.pop("pending_exam_action", None)

if action and require_documents(vector_store):
    llm = StudyAssistantLLM(provider=selected_provider)
    with st.spinner("Preparing exam material from the uploaded documents..."):
        try:
            if action == "summary":
                retrieved = vector_store.retrieve(
                    summary_topic,
                    k=max(top_k, 6),
                    source=active_source,
                    mode=retrieval_mode,
                )
                if has_retrieved_context(retrieved.context):
                    output = llm.generate_summary(summary_topic, retrieved.context)
                else:
                    output = insufficient_context_message()
            elif action == "mcqs":
                retrieved = vector_store.representative_context(
                    max_chunks=20,
                    source=active_source,
                )
                output = llm.generate_mcqs(int(mcq_count), retrieved.context)
            elif action == "quiz":
                retrieved = vector_store.representative_context(
                    max_chunks=20,
                    source=active_source,
                )
                raw_quiz = llm.generate_quiz_json(int(quiz_count), retrieved.context)
                questions = parse_quiz_questions(raw_quiz)
                st.session_state.quiz = {
                    "questions": questions,
                    "current": 0,
                    "answers": {},
                    "score": 0,
                    "submitted": {},
                    "sources": retrieved.sources,
                }
                output = f"Quiz created with {len(questions)} questions. Start below."
            elif action == "viva":
                retrieved = vector_store.representative_context(
                    max_chunks=16,
                    source=active_source,
                )
                output = llm.generate_viva_questions(retrieved.context)
            else:
                retrieved = vector_store.representative_context(
                    max_chunks=18,
                    source=active_source,
                )
                output = llm.generate_study_notes(retrieved.context)
        except MissingApiKeyError as exc:
            retrieved = vector_store.representative_context(
                max_chunks=4,
                source=active_source,
            )
            output = str(exc)
        except Exception as exc:
            retrieved = vector_store.representative_context(
                max_chunks=4,
                source=active_source,
            )
            output = f"Something went wrong while generating the material: {exc}"

    st.session_state.exam_output = {
        "action": action,
        "content": output,
        "sources": [] if action == "quiz" else retrieved.sources,
    }

prompt = st.session_state.pop("pending_question", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    if require_documents(vector_store):
        llm = StudyAssistantLLM(provider=selected_provider)
        with st.spinner("Searching your notes and generating an answer..."):
            try:
                retrieved = vector_store.retrieve(
                    prompt,
                    k=top_k,
                    source=active_source,
                    mode=retrieval_mode,
                )
                if has_retrieved_context(retrieved.context):
                    answer = llm.answer_question(prompt, retrieved.context)
                else:
                    answer = insufficient_context_message()
            except MissingApiKeyError as exc:
                retrieved = vector_store.retrieve(
                    prompt,
                    k=top_k,
                    source=active_source,
                    mode=retrieval_mode,
                )
                answer = (
                    str(exc)
                    if has_retrieved_context(retrieved.context)
                    else insufficient_context_message()
                )
            except Exception as exc:
                retrieved = vector_store.retrieve(
                    prompt,
                    k=top_k,
                    source=active_source,
                    mode=retrieval_mode,
                )
                if has_retrieved_context(retrieved.context):
                    answer = f"Something went wrong while generating the answer: {exc}"
                else:
                    answer = insufficient_context_message()

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": retrieved.sources,
            }
        )

exam_output = st.session_state.get("exam_output")

if active_tab == "chat":
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_sources(message.get("sources", []))

elif active_tab == "summary":
    if exam_output and exam_output["action"] == "summary":
        st.subheader("Generated Summary")
        st.markdown(exam_output["content"])
        render_sources(exam_output.get("sources", []))

elif active_tab == "mcqs":
    if exam_output and exam_output["action"] == "mcqs":
        st.subheader("Generated MCQs")
        render_mcq_cards(exam_output["content"])
        render_sources(exam_output.get("sources", []))

elif active_tab == "quiz":
    if exam_output and exam_output["action"] == "quiz":
        st.subheader("Interactive Quiz")
        st.markdown(exam_output["content"])
    render_quiz_panel()

elif active_tab == "viva":
    if exam_output and exam_output["action"] == "viva":
        st.subheader("Generated Viva Questions")
        render_viva_cards(exam_output["content"])
        render_sources(exam_output.get("sources", []))

elif active_tab == "notes":
    if exam_output and exam_output["action"] == "notes":
        st.subheader("Generated Study Notes")
        st.markdown(exam_output["content"])
        render_sources(exam_output.get("sources", []))

st.markdown("</div>", unsafe_allow_html=True)
