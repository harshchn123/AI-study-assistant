from pathlib import Path
import base64
import html
import textwrap


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 54
MARGIN_TOP = 58
MARGIN_BOTTOM = 54
LINE_HEIGHT = 14


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode(
        "cp1252", errors="replace"
    ).decode("cp1252")


def wrap(text: str, width: int = 92) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    for part in text.splitlines():
        if not part.strip():
            lines.append("")
        else:
            lines.extend(textwrap.wrap(part, width=width, replace_whitespace=True))
    return lines


class SimplePdf:
    def __init__(self) -> None:
        self.pages: list[list[str]] = []

    def add_page(self, lines: list[tuple[str, int, str]]) -> None:
        ops: list[str] = []
        y = PAGE_HEIGHT - MARGIN_TOP
        for text, size, font in lines:
            if text == "__PAGE_BREAK__":
                break
            for line in wrap(text, width=max(45, int(92 * 11 / size))):
                if y < MARGIN_BOTTOM:
                    break
                ops.append(f"BT /{font} {size} Tf {MARGIN_X:.2f} {y:.2f} Td ({esc(line)}) Tj ET")
                y -= LINE_HEIGHT if size <= 11 else LINE_HEIGHT + 4
            if size >= 14:
                y -= 8
            elif text == "":
                y -= 4
        self.pages.append(ops)

    def write(self, path: Path) -> None:
        objects: list[bytes] = []

        def add_obj(body: str | bytes) -> int:
            if isinstance(body, str):
                body = body.encode("cp1252", errors="replace")
            objects.append(body)
            return len(objects)

        f1 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>")
        f2 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>")
        f3 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        content_ids: list[int] = []
        page_ids: list[int] = []
        for page in self.pages:
            stream = "\n".join(page).encode("cp1252", errors="replace")
            content_ids.append(
                add_obj(
                    b"<< /Length "
                    + str(len(stream)).encode("ascii")
                    + b" >>\nstream\n"
                    + stream
                    + b"\nendstream"
                )
            )
            page_ids.append(0)

        pages_id = len(objects) + len(page_ids) + 1
        for index, content_id in enumerate(content_ids):
            page_ids[index] = add_obj(
                "<< /Type /Page "
                f"/Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {f1} 0 R /F2 {f2} 0 R /F3 {f3} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )

        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        pages_id = add_obj(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
        catalog_id = add_obj(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for object_id, body in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
            pdf.extend(body)
            pdf.extend(b"\nendobj\n")

        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            (
                "trailer\n"
                f"<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
                "startxref\n"
                f"{xref}\n%%EOF\n"
            ).encode("ascii")
        )
        path.write_bytes(pdf)


def h(text: str) -> tuple[str, int, str]:
    return (text, 16, "F2")


def sh(text: str) -> tuple[str, int, str]:
    return (text, 13, "F2")


def p(text: str) -> tuple[str, int, str]:
    return (text, 11, "F1")


def b(text: str) -> tuple[str, int, str]:
    return ("- " + text, 11, "F1")


def c(text: str) -> tuple[str, int, str]:
    return (text, 10, "F3")


def page_number(label: str) -> tuple[str, int, str]:
    return (label, 11, "F1")


def build_pages() -> list[list[tuple[str, int, str]]]:
    pages: list[list[tuple[str, int, str]]] = []

    pages.append([
        p("(i)"),
        ("AI STUDY ASSISTANT USING RAG", 18, "F2"),
        p(""),
        p("Project report submitted in partial fulfillment of the requirement for the degree of"),
        ("BACHELOR OF TECHNOLOGY", 14, "F2"),
        ("IN", 14, "F2"),
        ("INFORMATION TECHNOLOGY", 14, "F2"),
        p(""),
        p("By:"),
        ("Aryan Sharma (16222990012)", 13, "F2"),
        ("Harshita Chauhan (16222990024)", 13, "F2"),
        p(""),
        p("UNDER THE GUIDANCE OF:"),
        ("Dr. Akshay Bhardwaj", 12, "F2"),
        p(""),
        p("UNIVERSITY INSTITUTE OF TECHNOLOGY"),
        p("HIMACHAL PRADESH UNIVERSITY, SHIMLA"),
        p("(June, 2026)"),
    ])

    pages.append([p("(ii)"), p("Copyright © UIT, HPU Shimla, INDIA, 2026")])

    pages.append([
        p("(iii)"),
        h("TABLE OF CONTENTS"),
        p("CAPTION                                                        PAGE NO."),
        p("DECLARATION                                                    (v)"),
        p("ACKNOWLEDGMENT                                                 (vi)"),
        p("LIST OF FIGURES                                                (vii)"),
        p("LIST OF TABLES                                                 (viii)"),
        p("ABSTRACT                                                       (ix)"),
        p("CHAPTER-1: INTRODUCTION                                        1-4"),
        p("1.1 Relevance of the Project                                   1"),
        p("1.2 Problem Statement                                          2"),
        p("1.3 Objective                                                  2"),
        p("1.4 Scope of the Project                                       3"),
        p("1.5 Methodology                                                4"),
        p("CHAPTER-2: PROJECT OVERVIEW                                    5-9"),
        p("2.1 Literature Survey                                          5"),
        p("2.2 Problem Description                                        7"),
        p("2.3 Requirements Gathering                                     8"),
        p("2.4 Data Source                                                9"),
    ])

    pages.append([
        p("(iv)"),
        p("CHAPTER-3: REQUIREMENTS SPECIFICATION                          10-15"),
        p("3.1 Functional Requirements                                    10"),
        p("3.1.1 Web Application                                          10"),
        p("3.2 Non-Functional Requirements                                11"),
        p("3.2.1 Performance and Reliability                              11"),
        p("3.3 Software Requirements                                      12"),
        p("3.3.1 Programming Language                                     12"),
        p("3.3.2 Libraries                                                12"),
        p("3.3.3 Platform and IDE                                         13"),
        p("3.3.4 Design and Implementation Constraints                    13"),
        p("3.3.5 Assumptions and Dependencies                             14"),
        p("3.4 Hardware Requirements                                      14"),
        p("3.5 Cost-Benefit Analysis                                      15"),
        p("CHAPTER-4: ARCHITECTURE AND DESIGN                             16-25"),
        p("4.1 System Architecture                                        16"),
        p("4.1.1 RAG Pipeline Flow                                        17"),
        p("4.1.2 PDF Processing and OCR Flow                              18"),
        p("4.2 Data Flow Diagram                                          19"),
        p("4.3 Use Case Diagram                                           20"),
        p("4.4 Sequence Diagram                                           21"),
        p("4.5 ER Diagram and Data Model                                  22"),
        p("4.6 Component/Deployment Diagram                               23"),
        p("4.7 Activity Diagram                                           24"),
        p("CHAPTER-5: IMPLEMENTATION                                      26-33"),
        p("CHAPTER-6: RESULTS AND DISCUSSION                              34-38"),
        p("CHAPTER-7: VERIFICATION AND VALIDATION                         39-40"),
        p("7.1 Testing Methodologies                                      39"),
        p("7.2 Defect Analysis                                            39"),
        p("7.3 Testing Tables and Quality Factor Analysis                 40"),
        p("CHAPTER-8: CONCLUSION                                          41"),
        p("CHAPTER-9: FUTURE WORK                                         41"),
        p("CHAPTER-10: REFERENCES                                         41"),
    ])

    pages.append([
        p("(v)"),
        h("DECLARATION"),
        p("We hereby declare that the work reported in the B.Tech. Project Report entitled “AI Study Assistant using RAG” submitted at the University Institute of Technology, Himachal Pradesh University, Shimla is an authentic record of our work carried out as a major final year project."),
        p("The project has been developed using Python, Streamlit, Gemini API, LangChain-style chunking, SQLite indexing, optional ChromaDB semantic search, OCR processing, and retrieval-augmented generation techniques."),
        p("We have not submitted this work elsewhere for any other degree or diploma. All sources, tools, libraries, and documentation referred to during the development of this work have been acknowledged in the report."),
        p(""),
        p("Aryan Sharma"),
        p("Roll No.: 16222990012"),
        p("Harshita Chauhan"),
        p("Roll No.: 16222990024"),
        p(""),
        p("This is to certify that the above statement made by the candidates is correct to the best of my knowledge."),
        p(""),
        p("Dr. Akshay Bhardwaj"),
        p("Date:"),
    ])

    pages.append([
        p("(vi)"),
        h("ACKNOWLEDGMENT"),
        p("We take this opportunity to express our sincere gratitude to the University Institute of Technology, Himachal Pradesh University, Shimla, for providing the academic platform and technical environment to complete this major project."),
        p("We are grateful to Dr. Akshay Bhardwaj for his valuable guidance, support, and encouragement throughout the development of this work. His suggestions helped in improving the technical scope, usability, and presentation of the project."),
        p("We would also like to thank the Department of Information Technology for providing a strong foundation in programming, databases, software engineering, artificial intelligence, and web technologies. This foundation made it possible to design and implement a practical AI-based study assistant."),
        p("Finally, we express our heartfelt thanks to our parents, friends, and classmates for their moral support and continuous motivation during the completion of this project."),
    ])

    pages.append([
        p("(vii)"),
        h("LIST OF FIGURES"),
        p("Title                                                         Page No."),
        p("System Architecture of AI Study Assistant                     16"),
        p("RAG Pipeline Flow                                             17"),
        p("PDF Processing and OCR Flow                                   18"),
        p("Data Flow Diagram                                             19"),
        p("Use Case Diagram                                              20"),
        p("Sequence Diagram for Chat with PDF                            21"),
        p("ER Diagram and Data Model                                     22"),
        p("Component/Deployment Diagram                                  23"),
        p("Activity Diagram                                              24"),
        p("Streamlit User Interface                                      34"),
        p("Interactive Quiz Mode                                         36"),
        p("Testing and Validation Flow                                   39"),
    ])

    pages.append([
        p("(viii)"),
        h("LIST OF TABLES"),
        p("Title                                                         Page No."),
        p("Agile Methodology                                             4"),
        p("Functional Requirements                                       10"),
        p("Software Requirements                                         12"),
        p("Hardware Requirements                                         14"),
        p("Cost-Benefit Analysis                                         15"),
        p("Unit Testing                                                  40"),
        p("Quality Factor Analysis                                       40"),
    ])

    pages.append([
        p("(ix)"),
        h("ABSTRACT"),
        p("The AI Study Assistant using RAG is a web-based application developed to help students interact with their own study material through an intelligent chatbot. The system allows students to upload PDF notes, books, research papers, lecture notes, printed scans, and handwritten scanned notes. The uploaded document is processed, converted into chunks, indexed locally, and used as the knowledge base for question answering and exam preparation."),
        p("The project uses Retrieval-Augmented Generation so that the answer generation process is grounded in the uploaded document instead of relying only on the general knowledge of a large language model. The application supports Gemini-based OCR for scanned and handwritten PDFs, fast keyword retrieval through SQLite, optional ChromaDB semantic search, source citation, chapter summaries, MCQ generation, viva questions, revision notes, and an interactive quiz mode with scoring."),
        p("The system is implemented using Python and Streamlit. The backend modules include PDF loading, OCR processing, text chunking, indexing, retrieval, and LLM communication. The project demonstrates the practical use of artificial intelligence, OCR, natural language processing, and software engineering principles in the education domain."),
    ])

    body_pages = chapter_pages()
    pages.extend(body_pages)
    return pages


def chapter_pages() -> list[list[tuple[str, int, str]]]:
    return [
        [page_number("1"), h("CHAPTER 1"), h("INTRODUCTION"), p("In the present academic environment, students increasingly depend on digital documents for learning. Lecture notes, textbooks, research papers, scanned photocopies, handwritten classroom notes, and examination material are commonly stored as PDF files. Although these documents contain useful information, manually searching them during revision is time consuming."), p("The AI Study Assistant using RAG has been developed to solve this problem. It provides a web-based interface where students can upload study material and interact with it through a chatbot. The system does not simply answer from general internet knowledge; it retrieves relevant content from the uploaded document and uses that content as the basis for generating answers."), p("The application is especially useful during examination preparation because it can generate summaries, important concepts, MCQs, viva questions, revision notes, and interactive quizzes from the uploaded material. The inclusion of OCR allows the system to work with printed scanned PDFs and handwritten scanned notes."), sh("1.1 Relevance of the Project"), p("The relevance of the project lies in the increasing need for personalized, document-based learning tools. A student may have multiple PDFs for a subject, but finding exact answers or generating exam-oriented practice material from them requires effort. A document-aware AI assistant reduces this effort by making the study material searchable and conversational.")],
        [page_number("2"), sh("1.2 Problem Statement"), p("Students often face difficulty in extracting important information from large PDF documents. Traditional PDF search only works with exact keywords and does not provide explanations. General AI chatbots may generate good answers, but the answers may not be based on the student's specific notes. This can create confusion when preparing for exams."), p("The problem is more serious when the study material is scanned or handwritten. Such documents do not contain selectable text, so normal PDF extraction fails. Therefore, a system is required that can process both text PDFs and scanned PDFs, retrieve relevant content, and generate accurate study assistance from the uploaded material."), sh("1.3 Objective"), b("To develop a Streamlit-based AI Study Assistant for students."), b("To allow PDF upload and processing through a simple web interface."), b("To support text PDFs, printed scanned PDFs, and handwritten scanned notes."), b("To implement OCR using Gemini for image-based PDF pages."), b("To build a fast local document index for quick retrieval."), b("To optionally support ChromaDB semantic vector search."), b("To generate summaries, MCQs, viva questions, revision notes, and quizzes.")],
        [page_number("3"), sh("1.4 Scope of the Project"), p("The project focuses on building an academic assistant for document-based learning. The system supports PDF upload, extraction of text, OCR for scanned pages, chunking of document content, retrieval of relevant chunks, and LLM-based answer generation. The application is designed for students preparing for examinations, viva voce, assignments, and quick revision."), p("The scope includes local execution through Streamlit as well as cloud deployment through platforms such as Streamlit Community Cloud. The application stores uploaded document chunks in a local SQLite index for fast performance. It can use ChromaDB and Sentence Transformers when semantic retrieval is required. However, for demonstration and normal usage, keyword retrieval is kept as the default because it is faster and lighter."), p("The system does not attempt to replace teachers or textbooks. It is intended as an assistant that helps students revise and understand the uploaded study material more efficiently.")],
        [page_number("4"), sh("1.5 Methodology"), p("The project follows an agile methodology where development is divided into small functional modules. First, the Streamlit interface and PDF upload module were created. Then PDF extraction, OCR support, retrieval, LLM response generation, and exam tools were added incrementally."), p("Table: Agile Methodology"), c("Requirement Gathering  | Study PDF chatbot problem and identify student needs"), c("Planning               | Decide modules: UI, PDF loader, OCR, retriever, chatbot"), c("Development            | Implement Streamlit interface and backend utilities"), c("Testing                | Test PDF upload, OCR, retrieval, summaries, MCQs, quiz"), c("Optimization           | Add SQLite fast index and optional semantic indexing"), c("Deployment Planning    | Prepare .gitignore, secrets example, and cloud-ready settings"), p("This methodology allowed continuous testing and improvement. Performance issues such as slow embedding generation were solved by introducing a production-style fast local index.")],
        [page_number("5"), h("CHAPTER 2"), h("PROJECT OVERVIEW"), sh("2.1 Literature Survey"), p("Artificial intelligence has become an important tool in the education sector. AI-based tutoring systems, question-answering systems, and document summarization tools are increasingly used to support self-learning. Retrieval-Augmented Generation is one of the most effective approaches for document-based AI applications because it combines information retrieval with language generation."), p("In a RAG system, the document is first divided into chunks. When the user asks a question, the system retrieves the most relevant chunks and sends them to the language model. This reduces hallucination because the model receives the required context from the user's own documents."), p("OCR is another important area related to this project. Optical Character Recognition converts image-based text into machine-readable text. Printed OCR is easier, while handwritten OCR is more challenging because handwriting styles vary widely. Modern multimodal language models such as Gemini can interpret images and are useful for scanned notes.")],
        [page_number("6"), sh("2.1 Literature Survey Continued"), p("Traditional document search systems use keyword matching. They are fast but may fail when the user's query uses different wording. Semantic search systems use embeddings to match meaning rather than exact words. However, embeddings require additional computation and model loading. For this project, both approaches are considered: a fast keyword index for quick demonstration and optional semantic indexing through ChromaDB."), p("Existing study assistant tools often require users to copy text manually or upload only clean PDFs. The proposed system improves this by supporting OCR for scanned documents and offering exam-specific tools. The project is therefore a practical combination of OCR, retrieval, natural language processing, and web application development."), p("The literature survey shows that RAG-based systems are suitable for educational document understanding because they can ground model responses in trusted source material.")],
        [page_number("7"), sh("2.2 Problem Description"), p("The main problem addressed by this project is the difficulty faced by students while revising large and mixed-format study documents. Students may have typed PDFs, photocopied notes, research papers, or handwritten notebook scans. These documents are not easy to search manually."), p("A normal chatbot does not know the contents of the student's notes unless the content is supplied. A normal PDF reader cannot create summaries, MCQs, viva questions, or quizzes. The proposed system bridges this gap by converting uploaded documents into a searchable knowledge base and then using an LLM to generate study-oriented responses."), p("The system also handles the practical issue of speed. Embedding-based vector search is powerful but can be slow during a classroom demo. Therefore, the project uses a fast local SQLite index by default and keeps semantic indexing optional.")],
        [page_number("8"), sh("2.3 Requirements Gathering"), p("The requirements were gathered by analyzing the expected workflow of a student. A student should be able to upload a PDF, process it, ask questions, generate notes, and practice through MCQs or quizzes. The application should be simple enough to run locally and deployable enough to be shown to teachers or classmates."), p("The following requirements were identified:"), b("A sidebar for PDF upload and processing controls."), b("Support for normal PDFs and scanned PDFs."), b("Dedicated handwritten notes OCR mode."), b("A chat interface for document-based question answering."), b("Exam tools for summary, MCQ, viva, notes, and quiz generation."), b("Source display so the student can see where content was retrieved from."), b("Configuration through environment variables and cloud secrets.")],
        [page_number("9"), sh("2.4 Data Source"), p("The primary data source for this project is the PDF file uploaded by the user. These PDFs may contain typed text, printed scanned pages, handwritten notes, lecture slides, research papers, notices, or textbook chapters. The system does not depend on a fixed dataset because it creates the knowledge base dynamically from user-provided documents."), p("For text-based PDFs, PyPDF is used to extract selectable text. For scanned PDFs, the page is rendered as an image using PyMuPDF and sent to Gemini OCR. For handwritten notes, the image is rendered at a higher resolution and processed with a special prompt designed for handwritten transcription."), p("Once extracted, the text is chunked and stored with metadata such as source file, page number, extraction method, and chunk index.")],
        [page_number("10"), h("CHAPTER 3"), h("REQUIREMENTS SPECIFICATION"), sh("3.1 Functional Requirements"), p("Functional requirements define what the system must do. The AI Study Assistant provides the following major functions:"), c("FR1  User shall upload one or more PDF files."), c("FR2  System shall save uploaded PDFs in the uploads directory."), c("FR3  System shall extract selectable PDF text using PyPDF."), c("FR4  System shall perform OCR on scanned pages when required."), c("FR5  System shall support handwritten notes OCR mode."), c("FR6  System shall split extracted text into chunks."), c("FR7  System shall store chunks in a local SQLite index."), c("FR8  System shall retrieve relevant chunks for a question."), c("FR9  System shall generate answers from retrieved context only."), c("FR10 System shall generate summaries, MCQs, viva questions, notes, and quiz questions.")],
        [page_number("11"), sh("3.2 Non-Functional Requirements"), p("Non-functional requirements define the quality attributes of the system. The application should be fast enough for demonstration, easy to use, reliable in handling different document formats, and maintainable through modular code."), b("Performance: The default keyword retrieval should respond quickly without loading heavy embedding models."), b("Usability: The interface should be understandable to students without technical training."), b("Reliability: The app should handle failed OCR or API errors gracefully."), b("Security: API keys should be stored in .env locally and Streamlit secrets in deployment."), b("Scalability: Multiple PDFs can be indexed, and a specific source can be selected for answering."), b("Maintainability: Code is divided into modules for PDF loading, retrieval, embeddings, and chatbot logic.")],
        [page_number("12"), sh("3.3 Software Requirements"), sh("3.3.1 Programming Language"), p("Python is used as the main programming language because it provides strong support for AI, web applications, OCR, PDF processing, and data handling. Python also has mature libraries for working with language models and vector databases."), sh("3.3.2 Libraries"), b("Streamlit for the web-based user interface."), b("PyPDF for extracting selectable text from PDF files."), b("PyMuPDF for rendering scanned PDF pages into images."), b("Pillow for image preprocessing in OCR workflows."), b("Requests for direct API communication with Gemini."), b("SQLite for fast local chunk indexing."), b("ChromaDB and Sentence Transformers for optional semantic search."), b("python-dotenv for environment variable loading.")],
        [page_number("13"), sh("3.3.3 Platform and IDE"), p("The project is developed on Windows using Python and Visual Studio Code. Streamlit is used to run the project locally in a browser at localhost. The same project can be deployed on Streamlit Community Cloud by pushing the code to GitHub and adding API keys through the secrets panel."), sh("3.3.4 Design and Implementation Constraints"), p("The system depends on the availability of a Gemini API key for OCR and answer generation. If internet connectivity or DNS resolution fails, Gemini OCR cannot be used. Handwritten OCR quality also depends on image clarity, lighting, handwriting style, and page resolution."), p("To reduce performance constraints, the project uses SQLite keyword retrieval by default and avoids embedding generation unless semantic indexing is specifically enabled.")],
        [page_number("14"), sh("3.3.5 Assumptions and Dependencies"), b("The user has a valid Gemini API key for OCR and LLM generation."), b("Uploaded PDFs contain either selectable text or readable scanned images."), b("The system has a working internet connection when Gemini OCR is used."), b("The browser can access the local Streamlit server."), b("For deployment, secrets are configured correctly in Streamlit Cloud."), sh("3.4 Hardware Requirements"), c("Processor        : Intel i3/i5 or equivalent"), c("RAM              : Minimum 4 GB, recommended 8 GB"), c("Storage          : 1 GB free space for project, uploads, and indexes"), c("Internet         : Required for Gemini API and cloud deployment"), c("Display          : Browser-compatible desktop or laptop screen")],
        [page_number("15"), sh("3.5 Cost-Benefit Analysis"), p("The project has low development and deployment cost because it uses open-source tools such as Python, Streamlit, PyPDF, PyMuPDF, SQLite, and ChromaDB. The main variable cost is the usage of Gemini API for OCR and text generation. For academic demonstration, this cost is limited because only a small number of PDFs are processed."), p("The benefit is significant for students because the system saves time during revision and provides multiple exam-preparation outputs from the same document. The application can be reused across subjects and can be deployed online for easy access during presentations."), p("Compared to manual study preparation, the system reduces searching effort, supports self-assessment, and improves access to scanned notes.")],
        [page_number("16"), h("CHAPTER 4"), h("ARCHITECTURE AND DESIGN"), sh("4.1 System Architecture"), p("The system follows a modular architecture in which every major responsibility is handled by a separate component. The Streamlit interface receives user input, the PDF loader extracts text or performs OCR, the retriever stores and searches document chunks, and the chatbot module communicates with the selected LLM. This separation makes the project easier to test, debug, and extend."), p("DIAGRAM:SYSTEM"), p("Figure: System Architecture of AI Study Assistant"), p("The architecture is suitable for local execution as well as deployment on Streamlit Cloud because only the LLM and OCR calls require an external API. Uploaded documents, extracted chunks, and retrieval indexes remain under the application's control.")],
        [page_number("17"), sh("4.1.1 RAG Pipeline Flow"), p("Retrieval-Augmented Generation is used to reduce unsupported answers. The complete PDF is not sent to the language model for every query. Instead, the document is processed once, divided into smaller chunks, and indexed. During question answering, only the most relevant chunks are retrieved and supplied as context to the LLM."), p("DIAGRAM:RAG"), p("Figure: RAG Pipeline Flow"), p("This approach improves accuracy because the generated answer is grounded in the uploaded study material. It also reduces token usage because the model receives only selected context instead of the entire document.")],
        [page_number("18"), sh("4.1.2 PDF Processing and OCR Flow"), p("The PDF processing module supports both selectable text PDFs and scanned image PDFs. First, the system tries to extract text using PyPDF. If the extracted text is empty, weak, or only page numbers, the page is rendered as an image and sent for OCR. Handwritten notes use higher image resolution and preprocessing to improve recognition quality."), p("DIAGRAM:OCR"), p("Figure: PDF Processing and OCR Flow"), p("This flow is important because many academic notes are scanned or handwritten. OCR support allows the assistant to convert such images into usable text for summaries, MCQs, viva questions, and chat-based answers.")],
        [page_number("19"), sh("4.2 Data Flow Diagram"), p("The Data Flow Diagram shows how information moves through the AI Study Assistant. The student uploads a PDF and asks questions through the Streamlit interface. The document is processed by the PDF/OCR module, stored in the local index, retrieved according to the query, and then passed to the LLM for response generation."), p("DIAGRAM:DFD"), p("Figure: Data Flow Diagram"), p("The LLM does not directly access the upload folder. It receives only the selected retrieved chunks. This design keeps the answer-generation process focused on relevant document content and reduces unrelated responses.")],
        [page_number("20"), sh("4.3 Use Case Diagram"), p("The Use Case Diagram represents the interaction between the student and the system. The student can upload PDFs, process documents, ask questions, generate exam material, start quiz mode, review answers, and reset the vector database. These use cases cover the complete learning workflow from document preparation to self-assessment."), p("DIAGRAM:USE_CASE"), p("Figure: Use Case Diagram"), p("The same uploaded document can be reused for multiple study activities. This makes the application more useful than a normal PDF reader because it supports explanation, revision, practice, and evaluation.")],
        [page_number("21"), sh("4.4 Sequence Diagram"), p("The Sequence Diagram explains the order of execution when a student asks a question. After the PDF is indexed, the user query is sent from the interface to the retriever. The retriever returns relevant chunks, and the chatbot module combines those chunks with the question before calling the LLM. The generated answer is returned to the Streamlit interface."), p("DIAGRAM:SEQUENCE"), p("Figure: Sequence Diagram for Chat with PDF"), p("This sequence ensures that the answer is produced only after retrieval. Therefore, the chatbot behaves as a document-grounded assistant rather than a general chatbot.")],
        [page_number("22"), sh("4.5 ER Diagram and Data Model"), p("The ER diagram represents the logical data model used by the project. A PDF document contains pages, pages are divided into chunks, chunks are indexed for retrieval, and quiz or chat outputs are generated using retrieved chunks. This model also stores metadata such as source file, page number, chunk index, and extraction method."), p("DIAGRAM:ER"), p("Figure: ER Diagram and Data Model"), p("The data model supports source filtering, page-level citation, OCR tracking, and future expansion such as persistent chat history, student login, subject-wise folders, and quiz analytics.")],
        [page_number("23"), sh("4.6 Component/Deployment Diagram"), p("The Component and Deployment Diagram shows where the application components run. In local mode, the browser, Streamlit app, upload folder, SQLite index, and optional ChromaDB index run on the user's machine. The Gemini API is accessed over the internet for OCR and LLM response generation. In cloud deployment, Streamlit hosts the app and secrets are stored securely in platform settings."), p("DIAGRAM:DEPLOYMENT"), p("Figure: Component/Deployment Diagram"), p("This deployment structure keeps the project simple for college demonstration while still being ready for online access through GitHub and Streamlit Community Cloud.")],
        [page_number("24"), sh("4.7 Activity Diagram"), p("The Activity Diagram shows the end-to-end workflow followed by the user. The process starts with PDF upload, continues through OCR decision-making and indexing, and then branches into chat, summary, MCQ, viva, notes, or quiz generation. The user can repeat question-answering and exam-tool activities without reprocessing the document every time."), p("DIAGRAM:ACTIVITY"), p("Figure: Activity Diagram"), p("The activity flow highlights that document processing is a one-time step, while retrieval and generation can be performed repeatedly. This improves usability and reduces waiting time after the first indexing operation.")],
        [page_number("25"), sh("Design Considerations"), p("The design emphasizes speed, clarity, and reliability. The first version used embeddings for all PDF processing, but this caused slow first loading. The design was improved by introducing SQLite keyword indexing as the default production demo mode. This makes processing fast while keeping semantic search available as an optional advanced feature."), p("The OCR design also evolved. Printed OCR and handwritten OCR require different prompts and image preprocessing. The handwritten mode renders pages at higher resolution, increases contrast, and instructs Gemini to transcribe handwritten study notes carefully.")],
        [page_number("26"), h("CHAPTER 5"), h("IMPLEMENTATION"), p("Implementation is the stage where the planned system architecture is converted into a working application. The project has been implemented in modular form so that each file has a specific responsibility."), sh("Main Files"), b("app.py: Streamlit frontend, session state, quiz mode, and workflow controls."), b("pdf_loader.py: PDF saving, text extraction, OCR rendering, Gemini OCR, local OCR hooks, and caching."), b("retriever.py: SQLite indexing, chunking, keyword retrieval, and optional semantic search."), b("chatbot.py: Gemini/OpenAI/OpenRouter communication and exam prompt generation."), b("embeddings.py: SentenceTransformer embedding function for ChromaDB."), p("The implementation is designed to run locally and also support deployment through Streamlit Cloud secrets.")],
        [page_number("27"), sh("PDF Upload Implementation"), p("The PDF upload module is implemented using Streamlit's file uploader component. Users can upload one or more PDF files. The uploaded file is saved in the uploads directory using a safe filename. Once saved, the file path is passed to the retriever module for processing."), p("The app provides controls for OCR scanned pages, OCR type, force OCR all pages, retrieval mode, and semantic index building. These controls allow the same application to handle normal PDFs, scanned printed PDFs, and handwritten scanned notes."), p("Errors during processing are caught and displayed in the sidebar, so the user can understand whether the issue is related to OCR, API keys, network, or document format.")],
        [page_number("28"), sh("Text Extraction and OCR Implementation"), p("For selectable PDFs, PyPDF extracts text from each page. If no valid text is found, OCR is used. In handwritten mode, the application checks whether the extracted text is too small or likely to be only page numbers. If so, OCR is forced even though PyPDF returned a small amount of text."), p("The OCR module renders PDF pages into images using PyMuPDF. For handwritten notes, the image is converted to grayscale, auto-contrasted, sharpened, and filtered before being sent to Gemini. OCR output is cached per page to avoid repeated API calls."), p("This implementation is important because handwritten PDFs often contain only image data and may have misleading extracted page numbers.")],
        [page_number("29"), sh("Indexing and Retrieval Implementation"), p("The system stores chunks in SQLite by default. Each row contains chunk id, source filename, page number, chunk index, extraction method, and chunk text. SQLite is chosen for production demo speed because it avoids loading heavy embedding models during PDF processing."), p("Keyword retrieval scores chunks based on important query terms and exact phrase matches. This makes retrieval extremely fast. For advanced semantic retrieval, the user can enable semantic indexing. In that case, ChromaDB and Sentence Transformers are used to store vector embeddings."), p("The user can select a specific PDF from the Answer From dropdown, which prevents answers from mixing content from older uploaded documents.")],
        [page_number("30"), sh("LLM Integration Implementation"), p("The chatbot module communicates with Gemini through REST API calls. API keys are passed through request headers and are not printed in error messages. The system includes retry and fallback logic for temporary model overloads."), p("Prompts are designed to keep responses grounded in the uploaded document context. If the answer is not present in the retrieved context, the model is instructed to say that it could not find the answer in the uploaded document."), p("The same LLM wrapper is reused for question answering, summary generation, MCQ generation, viva question generation, revision notes, and quiz JSON generation.")],
        [page_number("31"), sh("Exam Tools Implementation"), p("The exam tools module is implemented in the right panel of the Streamlit interface. The user can generate a summary, MCQs, viva questions, notes, or an interactive quiz. Each tool retrieves document context first and then sends a task-specific prompt to the LLM."), b("Summary generation creates key concepts, definitions, formulas, and exam points."), b("MCQ generation creates questions with four options and answers."), b("Viva generation creates oral examination questions with model answers."), b("Notes generation creates short revision notes."), b("Quiz mode creates JSON-based questions for interactive scoring.")],
        [page_number("32"), sh("Interactive Quiz Mode Implementation"), p("Interactive quiz mode is one of the latest features added to the project. The LLM generates a structured JSON list of MCQs. The application parses this JSON and stores the questions in Streamlit session state."), p("The quiz interface shows one question at a time. The student selects an option and submits the answer. The system immediately displays whether the answer is correct, shows the correct option, provides an explanation, updates the score, and allows the student to move to the next question."), p("At the end of the quiz, the final score and answer review are displayed. This feature makes the project more interactive and useful for exam preparation.")],
        [page_number("33"), sh("Deployment Preparation"), p("The project includes a .gitignore file that prevents sensitive and generated files from being uploaded to GitHub. The .env file, uploads directory, ChromaDB files, and cache files are excluded. A secrets.toml.example file is provided for Streamlit Cloud deployment."), p("For deployment, the code is pushed to GitHub. Streamlit Community Cloud can then deploy the app using app.py as the main file. API keys are added in the Streamlit secrets panel instead of being committed to GitHub."), p("The default deployment settings use Gemini OCR, keyword retrieval, and disabled semantic indexing for speed.")],
        [page_number("34"), h("CHAPTER 6"), h("RESULTS AND DISCUSSION"), p("The implemented system provides a working web interface for document-based study assistance. Users can upload PDFs, process them, select a document source, ask questions, and generate exam preparation material. The latest version also supports handwritten notes OCR and interactive quiz mode."), p("Figure: Streamlit User Interface"), p("The sidebar contains upload and processing controls. The main area contains the chat interface, while the right panel contains exam tools. This layout makes the application easy to demonstrate and use.")],
        [page_number("35"), sh("PDF Processing Results"), p("The application successfully processes normal text PDFs quickly because it uses PyPDF extraction and SQLite indexing. For scanned PDFs, OCR is performed through Gemini. For handwritten PDFs, the system can force OCR even when PyPDF extracts only page numbers."), p("During testing, a handwritten PDF created by a scanner app returned only page numbers from PyPDF. The project was improved to detect such weak text and trigger OCR. This demonstrates practical debugging and enhancement based on real document behavior."), p("OCR results depend on image quality, handwriting clarity, internet connectivity, and model availability.")],
        [page_number("36"), sh("Interactive Quiz Results"), p("The interactive quiz mode generates exam-style MCQs from retrieved document context. The user can answer each question and receive instant feedback. The final score helps students evaluate their preparation."), c("Question -> Student selects option -> Submit -> Correct/Wrong -> Explanation -> Score"), p("Figure: Interactive Quiz Mode"), p("This feature improves the educational value of the project because it changes the application from a passive chatbot into an active learning tool.")],
        [page_number("37"), sh("Performance Discussion"), p("Initial versions of the project were slow because embeddings were generated during every PDF processing step. This was improved by making SQLite keyword retrieval the default. In local testing, normal PDF processing became very fast, with retrieval taking only a few milliseconds after indexing."), p("Semantic indexing remains available as an optional feature for users who need meaning-based retrieval. This design balances speed and intelligence. For college demonstrations, keyword mode is preferred because it avoids unnecessary model loading delays.")],
        [page_number("38"), sh("Limitations Observed"), p("The system still depends on external LLM services for Gemini OCR and generation. If Gemini is overloaded or DNS resolution fails, OCR and answer generation may fail temporarily. Retry and fallback logic reduces this issue but cannot completely remove dependency on the external service."), p("Handwritten OCR is inherently difficult. Very unclear handwriting, low contrast images, shadows, tilted pages, or overlapping text may reduce transcription quality. However, the dedicated handwritten mode improves the chances of useful extraction.")],
        [page_number("39"), h("CHAPTER 7"), h("VERIFICATION AND VALIDATION"), p("Verification and validation ensure that the developed system meets its requirements and works correctly. Different modules were tested separately and then together. The testing process focused on PDF upload, OCR, indexing, retrieval, LLM generation, and quiz interaction."), sh("7.1 Testing Methodologies"), p("The project was tested using unit testing, integration testing, system testing, and usability testing. Manual testing was important because the application contains user interface workflows and external API interactions.")],
        [page_number("40"), sh("Unit Testing"), p("Table: Unit Testing"), c("T1 PDF save function              Input PDF file                 File saved in uploads       Pass"), c("T2 PyPDF extraction               Text PDF                       Text extracted              Pass"), c("T3 Blank scanned PDF detection    Image-only PDF                 OCR triggered               Pass"), c("T4 Handwritten weak text check     Page number only               OCR triggered               Pass"), c("T5 SQLite index creation           Extracted chunks               Chunks stored               Pass"), c("T6 Keyword retrieval               Query terms                    Relevant chunks returned    Pass"), c("T7 Quiz parser                     JSON response                  Questions parsed            Pass"), c("T8 Secret masking                  API key error path             Key not printed             Pass")],
        [page_number("41"), sh("Unit Testing Discussion"), p("Unit tests confirmed that individual components work as expected. The PDF loader correctly saves and processes files. The handwritten OCR detection logic correctly identifies page-number-only extraction as weak text. The SQLite retriever stores chunks and retrieves relevant context using keyword scoring."), p("The quiz parser is validated to ensure that the LLM output contains valid question, options, answer, and explanation fields. If invalid JSON is returned, the app displays an error instead of crashing.")],
        [page_number("42"), sh("Integration Testing"), p("Table: Integration Testing"), c("Scenario                         Steps                              Expected Result"), c("Text PDF chat                    Upload -> process -> ask query     Answer from selected PDF"), c("Scanned notice PDF               Upload -> OCR -> summary           OCR text summarized"), c("Handwritten notes PDF            Force OCR -> process                Handwritten pages OCR processed"), c("Exam tools                       Process -> generate MCQs            MCQs from context"), c("Quiz mode                        Generate -> answer questions        Score and explanations shown"), c("Source filtering                 Select one PDF -> ask question      No unrelated source mixed")],
        [page_number("43"), sh("System Testing"), p("System testing was performed by running the complete application through Streamlit. The user workflow was tested from upload to response generation. The app was also tested after restarts to ensure that cached OCR and indexed chunks continued to work correctly."), p("Important user-facing errors such as Gemini high demand, DNS failure, and model unavailability were handled with clearer messages. This improved reliability and made troubleshooting easier during demonstration."), p("The app was also checked for deployment readiness by cleaning .env, updating .gitignore, and preparing Streamlit secrets example.")],
        [page_number("44"), sh("7.2 Defect Analysis"), p("Several defects were identified and resolved during development. The first major issue was slow first loading due to forced embedding generation. This was solved by using SQLite keyword indexing as the default. The second issue was OCR skipping handwritten pages because PyPDF extracted page numbers. This was solved by adding force OCR and weak text detection."), p("Another defect was generic Gemini errors. The error handling was improved to show safe HTTP status messages without exposing API keys. Retry and fallback models were also added for Gemini overload errors.")],
        [page_number("45"), sh("7.3 Quality Factor Analysis"), c("Correctness  : Answers are grounded in retrieved document chunks."), c("Reliability  : Errors are handled gracefully with retry and fallback logic."), c("Efficiency  : SQLite keyword retrieval avoids slow embedding generation by default."), c("Integrity    : API keys are kept in .env or Streamlit secrets, not in GitHub."), c("Portability  : The app can run locally or on Streamlit Cloud."), c("Reusability  : Modules are separated and can be reused in other AI document apps."), c("Usability    : Streamlit interface provides upload, chat, exam tools, and quiz mode.")],
        [page_number("46"), h("CHAPTER 8"), h("CONCLUSION"), p("The AI Study Assistant using RAG successfully demonstrates how artificial intelligence can be applied to education. The system allows students to upload study material and interact with it through a chatbot. It supports normal PDFs, printed scanned PDFs, and handwritten notes through OCR."), p("The project implements a complete pipeline: PDF upload, text extraction, OCR, chunking, indexing, retrieval, LLM generation, and exam tools. The addition of interactive quiz mode makes the application more engaging and useful for self-assessment."), p("The use of fast SQLite indexing makes the application practical for demonstrations, while optional ChromaDB semantic indexing keeps the system extensible. Overall, the project provides a strong foundation for a real AI-powered study platform.")],
        [page_number("47"), h("CHAPTER 9"), h("FUTURE WORK"), p("Several enhancements can be added in future versions of the project. Student login can be implemented so that each student has a personal document library and chat history. A dashboard can show uploaded subjects, revision progress, quiz scores, and weak topics."), b("Add persistent user accounts and authentication."), b("Store chat history and quiz results permanently."), b("Generate downloadable PDF/DOCX study packs."), b("Add voice input and text-to-speech output."), b("Improve handwritten OCR through local OCR or specialized handwriting models."), b("Add subject-wise folders and document collections."), b("Deploy the system with cloud storage for persistent uploads."), b("Add analytics for weak topics and personalized recommendations.")],
        [page_number("48"), h("CHAPTER 10"), h("REFERENCES"), b("Python Software Foundation, Python Documentation."), b("Streamlit Documentation, Streamlit Community Cloud Deployment Guide."), b("Google Gemini API Documentation and Model Reference."), b("PyPDF Documentation for PDF Text Extraction."), b("PyMuPDF Documentation for PDF Rendering."), b("ChromaDB Documentation for Vector Databases."), b("Sentence Transformers Documentation."), b("LangChain Text Splitter Documentation."), b("SQLite Documentation."), b("Research and online resources related to Retrieval-Augmented Generation, OCR, and educational AI systems.")],
        [page_number("49"), h("APPENDIX A"), h("PROJECT CONFIGURATION"), p("The important environment configuration used in the project is shown below. API keys are not committed to GitHub and should be stored in .env locally or in Streamlit Cloud secrets during deployment."), c("LLM_PROVIDER=gemini"), c("GEMINI_MODEL=gemini-3.5-flash"), c("GEMINI_RETRIES=3"), c("GEMINI_OCR_MODEL=gemini-3.5-flash"), c("GEMINI_OCR_RETRIES=3"), c("OCR_PROVIDER=gemini"), c("OCR_RENDER_SCALE=1.4"), c("HANDWRITING_OCR_RENDER_SCALE=2.4"), c("RETRIEVAL_MODE=keyword"), c("SEMANTIC_INDEX_ON_PROCESS=false"), p("These settings are optimized for a fast professor demonstration.")],
        [page_number("50"), h("APPENDIX B"), h("DEMO WORKFLOW"), p("The recommended demonstration workflow is as follows:"), b("Run the Streamlit app."), b("Upload a normal PDF and process it quickly."), b("Ask a question and show grounded answer with source citation."), b("Upload or select a scanned/handwritten PDF."), b("Enable OCR scanned pages, select handwritten notes, and force OCR all pages."), b("Generate a summary and MCQs."), b("Start interactive quiz mode and answer questions."), b("Show final score and answer review."), p("This workflow demonstrates PDF processing, OCR, retrieval, LLM generation, exam preparation tools, and interactive assessment in a single project.")],
    ]


def build_markdown(pages: list[list[tuple[str, int, str]]]) -> str:
    output = ["# AI Study Assistant using RAG - Detailed Project Report", ""]
    for index, page in enumerate(pages, start=1):
        output.append(f"<!-- Page {index} -->")
        for text, size, _font in page:
            if text.startswith("DIAGRAM:"):
                output.append(f"[Diagram: {text.split(':', 1)[1].replace('_', ' ').title()}]")
            elif size >= 16:
                output.append(f"## {text}")
            elif size >= 13:
                output.append(f"### {text}")
            else:
                output.append(text)
        output.append("")
    return "\n".join(output)


def diagram_html(kind: str) -> str:
    diagrams = {
        "SYSTEM": """
<svg class="diagram-svg" viewBox="0 0 760 285" role="img" aria-label="System architecture diagram">
  <defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#111827"/></marker></defs>
  <rect x="18" y="42" width="112" height="54" rx="6"/><text x="74" y="65">Student</text><text x="74" y="83">Browser</text>
  <rect x="165" y="34" width="128" height="70" rx="6"/><text x="229" y="60">Streamlit</text><text x="229" y="80">Frontend</text>
  <rect x="335" y="28" width="138" height="82" rx="6"/><text x="404" y="55">PDF Loader</text><text x="404" y="75">OCR Module</text><text x="404" y="95">Chunking</text>
  <rect x="520" y="34" width="128" height="70" rx="6"/><text x="584" y="61">Retriever</text><text x="584" y="81">SQLite Index</text>
  <rect x="238" y="175" width="142" height="70" rx="6"/><text x="309" y="202">Chatbot</text><text x="309" y="222">Prompt Builder</text>
  <rect x="470" y="175" width="142" height="70" rx="6"/><text x="541" y="202">Gemini API</text><text x="541" y="222">OCR / LLM</text>
  <path d="M130 69 H165" marker-end="url(#arrow)"/><path d="M293 69 H335" marker-end="url(#arrow)"/><path d="M473 69 H520" marker-end="url(#arrow)"/>
  <path d="M584 104 C584 145 309 145 309 175" marker-end="url(#arrow)"/><path d="M380 210 H470" marker-end="url(#arrow)"/><path d="M238 210 C150 210 110 110 110 88" marker-end="url(#arrow)"/>
</svg>""",
        "RAG": """
<svg class="diagram-svg" viewBox="0 0 760 250" role="img" aria-label="RAG pipeline diagram">
  <defs><marker id="arrow2" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#111827"/></marker></defs>
  <rect x="20" y="48" width="105" height="54" rx="6"/><text x="72" y="70">Upload</text><text x="72" y="88">PDF</text>
  <rect x="155" y="48" width="110" height="54" rx="6"/><text x="210" y="70">Extract</text><text x="210" y="88">Text/OCR</text>
  <rect x="295" y="48" width="110" height="54" rx="6"/><text x="350" y="70">Split into</text><text x="350" y="88">Chunks</text>
  <rect x="435" y="48" width="110" height="54" rx="6"/><text x="490" y="70">Store</text><text x="490" y="88">Index</text>
  <rect x="575" y="48" width="130" height="54" rx="6"/><text x="640" y="70">Retrieve</text><text x="640" y="88">Context</text>
  <rect x="242" y="160" width="130" height="54" rx="6"/><text x="307" y="182">Question</text><text x="307" y="200">+ Context</text>
  <rect x="430" y="160" width="130" height="54" rx="6"/><text x="495" y="182">LLM</text><text x="495" y="200">Answer</text>
  <path d="M125 75 H155" marker-end="url(#arrow2)"/><path d="M265 75 H295" marker-end="url(#arrow2)"/><path d="M405 75 H435" marker-end="url(#arrow2)"/><path d="M545 75 H575" marker-end="url(#arrow2)"/>
  <path d="M640 102 C640 138 307 128 307 160" marker-end="url(#arrow2)"/><path d="M372 187 H430" marker-end="url(#arrow2)"/>
</svg>""",
        "OCR": """
<svg class="diagram-svg" viewBox="0 0 760 270" role="img" aria-label="PDF OCR flow diagram">
  <defs><marker id="arrow3" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#111827"/></marker></defs>
  <rect x="28" y="42" width="120" height="54" rx="6"/><text x="88" y="66">PDF Page</text>
  <rect x="190" y="42" width="132" height="54" rx="6"/><text x="256" y="64">PyPDF Text</text><text x="256" y="82">Extraction</text>
  <polygon points="390,35 475,70 390,105 305,70"/><text x="390" y="67">Useful</text><text x="390" y="83">Text?</text>
  <rect x="525" y="42" width="150" height="54" rx="6"/><text x="600" y="65">Use Text for</text><text x="600" y="83">Chunking</text>
  <rect x="230" y="165" width="135" height="54" rx="6"/><text x="297" y="188">Render Page</text><text x="297" y="206">as Image</text>
  <rect x="420" y="165" width="130" height="54" rx="6"/><text x="485" y="188">Gemini OCR</text><text x="485" y="206">Transcribe</text>
  <rect x="600" y="165" width="120" height="54" rx="6"/><text x="660" y="188">Clean Text</text><text x="660" y="206">Store</text>
  <path d="M148 69 H190" marker-end="url(#arrow3)"/><path d="M322 69 H305" marker-end="url(#arrow3)"/><path d="M475 70 H525" marker-end="url(#arrow3)"/><text x="498" y="60">Yes</text>
  <path d="M390 105 C390 135 297 135 297 165" marker-end="url(#arrow3)"/><text x="342" y="132">No / scan</text>
  <path d="M365 192 H420" marker-end="url(#arrow3)"/><path d="M550 192 H600" marker-end="url(#arrow3)"/>
</svg>""",
        "DFD": """
<svg class="diagram-svg" viewBox="0 0 760 300" role="img" aria-label="Data flow diagram">
  <defs><marker id="arrow4" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#111827"/></marker></defs>
  <rect x="22" y="115" width="95" height="52" rx="6"/><text x="70" y="145">Student</text>
  <circle cx="230" cy="140" r="50"/><text x="230" y="132">1.0</text><text x="230" y="150">Streamlit UI</text>
  <circle cx="405" cy="80" r="50"/><text x="405" y="72">2.0</text><text x="405" y="90">PDF/OCR</text>
  <circle cx="405" cy="210" r="50"/><text x="405" y="202">3.0</text><text x="405" y="220">Retriever</text>
  <circle cx="585" cy="140" r="50"/><text x="585" y="132">4.0</text><text x="585" y="150">LLM</text>
  <rect x="315" y="258" width="180" height="30"/><text x="405" y="278">D1: SQLite / Chroma Index</text>
  <path d="M117 132 H180" marker-end="url(#arrow4)"/><text class="tiny" x="150" y="116">PDF, Query</text>
  <path d="M260 105 L362 84" marker-end="url(#arrow4)"/><text class="tiny" x="310" y="73">Upload</text>
  <path d="M405 130 V160" marker-end="url(#arrow4)"/><text class="tiny" x="438" y="145">Chunks</text>
  <path d="M405 260 V258" marker-end="url(#arrow4)"/>
  <path d="M455 210 C500 210 530 178 548 160" marker-end="url(#arrow4)"/><text class="tiny" x="518" y="193">Context</text>
  <path d="M537 125 C450 115 330 115 278 130" marker-end="url(#arrow4)"/><text class="tiny" x="405" y="108">Answer</text>
  <path d="M180 153 H117" marker-end="url(#arrow4)"/>
</svg>""",
        "USE_CASE": """
<svg class="diagram-svg" viewBox="0 0 760 330" role="img" aria-label="Use case diagram">
  <line x1="78" y1="65" x2="78" y2="165"/><circle cx="78" cy="45" r="18"/><line x1="78" y1="92" x2="42" y2="125"/><line x1="78" y1="92" x2="114" y2="125"/><line x1="78" y1="165" x2="48" y2="220"/><line x1="78" y1="165" x2="108" y2="220"/><text x="78" y="252">Student</text>
  <rect x="190" y="28" width="520" height="270" rx="8"/><text x="450" y="52">AI Study Assistant</text>
  <ellipse cx="330" cy="92" rx="92" ry="25"/><text x="330" y="98">Upload PDF</text>
  <ellipse cx="560" cy="92" rx="98" ry="25"/><text x="560" y="98">Process PDF/OCR</text>
  <ellipse cx="330" cy="155" rx="92" ry="25"/><text x="330" y="161">Ask Question</text>
  <ellipse cx="560" cy="155" rx="98" ry="25"/><text x="560" y="161">Generate Summary</text>
  <ellipse cx="330" cy="218" rx="92" ry="25"/><text x="330" y="224">MCQ / Viva / Notes</text>
  <ellipse cx="560" cy="218" rx="98" ry="25"/><text x="560" y="224">Interactive Quiz</text>
  <path d="M118 115 L238 92"/><path d="M118 125 L238 155"/><path d="M118 138 L238 218"/><path d="M118 116 L462 92"/><path d="M118 130 L462 155"/><path d="M118 145 L462 218"/>
</svg>""",
        "SEQUENCE": """
<svg class="diagram-svg" viewBox="0 0 760 330" role="img" aria-label="Sequence diagram">
  <defs><marker id="arrow5" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#111827"/></marker></defs>
  <text x="72" y="30">Student</text><text x="210" y="30">Streamlit UI</text><text x="365" y="30">Retriever</text><text x="515" y="30">Chatbot</text><text x="660" y="30">Gemini API</text>
  <line x1="82" y1="45" x2="82" y2="305" class="life"/><line x1="230" y1="45" x2="230" y2="305" class="life"/><line x1="385" y1="45" x2="385" y2="305" class="life"/><line x1="535" y1="45" x2="535" y2="305" class="life"/><line x1="680" y1="45" x2="680" y2="305" class="life"/>
  <path d="M82 70 H230" marker-end="url(#arrow5)"/><text x="150" y="62">Ask question</text>
  <path d="M230 110 H385" marker-end="url(#arrow5)"/><text x="300" y="102">retrieve(query)</text>
  <path d="M385 150 H230" marker-end="url(#arrow5)"/><text x="300" y="142">chunks</text>
  <path d="M230 190 H535" marker-end="url(#arrow5)"/><text x="382" y="182">context + query</text>
  <path d="M535 230 H680" marker-end="url(#arrow5)"/><text x="608" y="222">generate</text>
  <path d="M680 260 H535" marker-end="url(#arrow5)"/><text x="608" y="252">answer</text>
  <path d="M535 290 H82" marker-end="url(#arrow5)"/><text x="310" y="282">display response</text>
</svg>""",
        "ER": """
<svg class="diagram-svg" viewBox="0 0 760 320" role="img" aria-label="ER diagram">
  <defs><marker id="arrow6" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#111827"/></marker></defs>
  <rect x="35" y="55" width="155" height="98" rx="4"/><text x="112" y="78">PDF_DOCUMENT</text><text class="left small" x="52" y="104">document_id PK</text><text class="left small" x="52" y="126">filename</text><text class="left small" x="52" y="148">uploaded_at</text>
  <rect x="300" y="55" width="160" height="118" rx="4"/><text x="380" y="78">PDF_PAGE</text><text class="left small" x="317" y="104">page_id PK</text><text class="left small" x="317" y="126">document_id FK</text><text class="left small" x="317" y="148">page_number</text><text class="left small" x="317" y="168">ocr_method</text>
  <rect x="575" y="55" width="155" height="118" rx="4"/><text x="652" y="78">CHUNK</text><text class="left small" x="592" y="104">chunk_id PK</text><text class="left small" x="592" y="126">page_id FK</text><text class="left small" x="592" y="148">chunk_text</text><text class="left small" x="592" y="168">chunk_index</text>
  <rect x="300" y="215" width="160" height="78" rx="4"/><text x="380" y="238">CHAT / QUIZ</text><text class="left small" x="317" y="264">query / answer</text><text class="left small" x="317" y="286">score / feedback</text>
  <path d="M185 101 H300" marker-end="url(#arrow6)"/><text x="242" y="92">1 to many</text>
  <path d="M450 111 H575" marker-end="url(#arrow6)"/><text x="512" y="102">1 to many</text>
  <path d="M575 165 C500 205 450 220 450 242" marker-end="url(#arrow6)"/><text x="530" y="214">uses</text>
</svg>""",
        "DEPLOYMENT": """
<svg class="diagram-svg" viewBox="0 0 760 300" role="img" aria-label="Deployment diagram">
  <defs><marker id="arrow7" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#111827"/></marker></defs>
  <rect x="35" y="70" width="150" height="70" rx="6"/><text x="110" y="98">Browser</text><text x="110" y="118">User Device</text>
  <rect x="250" y="35" width="250" height="205" rx="8"/><text x="375" y="62">Application Host</text>
  <rect x="285" y="85" width="180" height="42" rx="5"/><text x="375" y="112">Streamlit app.py</text>
  <rect x="285" y="145" width="80" height="42" rx="5"/><text x="325" y="171">uploads</text>
  <rect x="385" y="145" width="80" height="42" rx="5"/><text x="425" y="171">SQLite</text>
  <rect x="285" y="197" width="180" height="30" rx="5"/><text x="375" y="217">Optional ChromaDB</text>
  <rect x="570" y="80" width="150" height="70" rx="6"/><text x="645" y="108">Gemini API</text><text x="645" y="128">OCR + LLM</text>
  <path d="M185 105 H250" marker-end="url(#arrow7)"/><path d="M500 115 H570" marker-end="url(#arrow7)"/><path d="M570 132 H500" marker-end="url(#arrow7)"/>
</svg>""",
        "ACTIVITY": """
<svg class="diagram-svg" viewBox="0 0 760 330" role="img" aria-label="Activity diagram">
  <defs><marker id="arrow8" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#111827"/></marker></defs>
  <circle cx="70" cy="55" r="14" fill="#111827"/><rect x="125" y="35" width="110" height="42" rx="18"/><text x="180" y="62">Upload PDF</text>
  <rect x="285" y="35" width="120" height="42" rx="18"/><text x="345" y="62">Extract Text</text>
  <polygon points="485,28 565,56 485,84 405,56"/><text x="485" y="61">Need OCR?</text>
  <rect x="425" y="130" width="120" height="42" rx="18"/><text x="485" y="157">OCR Page</text>
  <rect x="595" y="35" width="120" height="42" rx="18"/><text x="655" y="62">Chunk/Index</text>
  <rect x="160" y="215" width="120" height="42" rx="18"/><text x="220" y="242">Ask / Tool</text>
  <rect x="330" y="215" width="120" height="42" rx="18"/><text x="390" y="242">Retrieve</text>
  <rect x="500" y="215" width="120" height="42" rx="18"/><text x="560" y="242">Generate</text>
  <circle cx="690" cy="236" r="16"/><circle cx="690" cy="236" r="9" fill="#111827"/>
  <path d="M84 55 H125" marker-end="url(#arrow8)"/><path d="M235 56 H285" marker-end="url(#arrow8)"/><path d="M405 56 H405" marker-end="url(#arrow8)"/>
  <path d="M565 56 H595" marker-end="url(#arrow8)"/><text x="572" y="47">No</text>
  <path d="M485 84 V130" marker-end="url(#arrow8)"/><text x="498" y="109">Yes</text>
  <path d="M545 151 C600 151 655 118 655 77" marker-end="url(#arrow8)"/>
  <path d="M655 77 C655 180 220 180 220 215" marker-end="url(#arrow8)"/><path d="M280 236 H330" marker-end="url(#arrow8)"/><path d="M450 236 H500" marker-end="url(#arrow8)"/><path d="M620 236 H674" marker-end="url(#arrow8)"/>
</svg>""",
    }
    svg = diagrams.get(kind.upper(), "")
    return f'<div class="diagram">{svg}</div>' if svg else ""


def split_index_row(text: str) -> tuple[str, str] | None:
    """Split generated index/list rows into caption and page-number columns."""
    compact = text.strip()
    if not compact:
        return None
    if compact.upper().startswith(("CAPTION", "TITLE")) and "PAGE" in compact.upper():
        header = compact.split()
        return header[0], "PAGE NO."
    if "  " not in text:
        return None

    parts = text.rstrip().rsplit(None, 1)
    if len(parts) != 2:
        return None
    caption, page = parts
    if page.startswith("(") or page[0].isdigit():
        return caption.strip(), page.strip()
    return None


def build_html(pages: list[list[tuple[str, int, str]]]) -> str:
    logo_src = logo_data_uri()
    page_html = []
    for index, page in enumerate(pages, start=1):
        folio = ""
        content = page
        if page and page[0][0].strip():
            first = page[0][0].strip()
            if first.startswith("(") or first.isdigit():
                folio = first
                content = page[1:]

        classes = "page"
        if index == 1:
            classes += " cover"
        if index == 2:
            classes += " copyright-page"
        if index in (3, 4):
            classes += " toc-page"
        if index in (7, 8):
            classes += " list-page"
        parts = [f'<section class="{classes}">']
        if folio:
            parts.append(f'<div class="folio">{html.escape(folio)}</div>')

        for text, size, font in content:
            safe = html.escape(text)
            if not text:
                parts.append('<div class="spacer"></div>')
            elif text.startswith("DIAGRAM:"):
                parts.append(diagram_html(text.split(":", 1)[1]))
            elif font == "F3":
                parts.append(f"<pre>{safe}</pre>")
            elif text.startswith("- "):
                parts.append(f"<p class=\"bullet\">{html.escape(text[2:])}</p>")
            elif (index in (3, 4, 7, 8)) and (row := split_index_row(text)):
                caption, page_no = row
                row_class = "index-row index-head" if caption.upper() in {"CAPTION", "TITLE"} else "index-row"
                parts.append(
                    f'<div class="{row_class}"><span>{html.escape(caption)}</span><span>{html.escape(page_no)}</span></div>'
                )
            elif size >= 16:
                parts.append(f"<h1>{safe}</h1>")
            elif size >= 13:
                parts.append(f"<h2>{safe}</h2>")
            else:
                parts.append(f"<p>{safe}</p>")

            if index == 1 and text == "Dr. Akshay Bhardwaj":
                parts.append(f'<img class="cover-logo" src="{logo_src}" alt="UIT HPU Logo">')

        parts.append("</section>")
        page_html.append("\n".join(parts))

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>AI Study Assistant using RAG - Detailed Project Report</title>
  <style>
    @page {{
      size: A4;
      margin: 0;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      background: #e5e7eb;
      color: #111827;
      font-family: "Times New Roman", Times, serif;
    }}
    .page {{
      width: 210mm;
      height: 296mm;
      page-break-after: always;
      background: white;
      margin: 0 auto;
      padding: 18mm 21mm 16mm 23mm;
      position: relative;
      overflow: hidden;
    }}
    .page:last-child {{
      page-break-after: auto;
    }}
    .page::after {{
      content: none;
    }}
    .folio {{
      position: absolute;
      bottom: 12mm;
      left: 0;
      right: 0;
      text-align: center;
      font-size: 10.5pt;
      color: #374151;
    }}
    h1 {{
      font-size: 18pt;
      margin: 0 0 6mm 0;
      text-align: center;
      font-weight: 700;
      letter-spacing: 0.2pt;
      text-transform: uppercase;
    }}
    h2 {{
      font-size: 13.5pt;
      margin: 4.5mm 0 2.4mm 0;
      font-weight: 700;
    }}
    p {{
      font-size: 11.3pt;
      line-height: 1.36;
      margin: 0 0 2.4mm 0;
      text-align: justify;
    }}
    .bullet {{
      padding-left: 8mm;
      text-indent: -5mm;
      text-align: left;
    }}
    .bullet::before {{
      content: "• ";
      font-weight: 700;
    }}
    pre {{
      font-family: "Courier New", monospace;
      font-size: 9.2pt;
      line-height: 1.35;
      max-height: 18mm;
      white-space: pre-wrap;
      margin: 0 0 2.6mm 0;
      padding: 2.4mm 3mm;
      background: #f8fafc;
      border-left: 1.2mm solid #64748b;
      color: #111827;
    }}
    .diagram {{
      width: 100%;
      margin: 4mm auto 4mm auto;
      padding: 2.5mm;
      border: 0.35mm solid #111827;
      background: #ffffff;
    }}
    .diagram-svg {{
      display: block;
      width: 100%;
      height: 72mm;
    }}
    .diagram-svg rect,
    .diagram-svg polygon,
    .diagram-svg circle,
    .diagram-svg ellipse {{
      fill: #ffffff;
      stroke: #111827;
      stroke-width: 1.4;
    }}
    .diagram-svg path,
    .diagram-svg line {{
      fill: none;
      stroke: #111827;
      stroke-width: 1.3;
    }}
    .diagram-svg .life {{
      stroke-dasharray: 5 4;
      stroke-width: 1;
    }}
    .diagram-svg text {{
      fill: #111827;
      font-family: "Times New Roman", Times, serif;
      font-size: 15px;
      text-anchor: middle;
      dominant-baseline: middle;
    }}
    .diagram-svg .left {{
      text-anchor: start;
    }}
    .diagram-svg .small {{
      font-size: 13px;
    }}
    .diagram-svg .tiny {{
      font-size: 12px;
    }}
    .spacer {{
      height: 4mm;
    }}
    .cover {{
      padding-top: 24mm;
      text-align: center;
    }}
    .cover h1 {{
      font-size: 21pt;
      margin-top: 11mm;
      margin-bottom: 14mm;
    }}
    .cover p {{
      text-align: center;
      font-size: 12pt;
      line-height: 1.65;
      margin-bottom: 4mm;
    }}
    .cover h2 {{
      text-align: center;
      font-size: 14pt;
      margin-top: 7mm;
    }}
    .cover-logo {{
      display: block;
      width: 34mm;
      height: 34mm;
      object-fit: contain;
      margin: 18mm auto 17mm auto;
    }}
    .copyright-page {{
      padding-top: 136mm;
    }}
    .copyright-page p {{
      text-align: center;
      font-weight: 700;
      font-size: 18pt;
      line-height: 1.3;
    }}
    .toc-page h1,
    .list-page h1 {{
      font-size: 16pt;
      margin-bottom: 7mm;
    }}
    .toc-page p,
    .list-page p {{
      text-align: left;
      font-size: 10.6pt;
      line-height: 1.16;
      margin-bottom: 1.25mm;
    }}
    .index-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 28mm;
      column-gap: 8mm;
      align-items: baseline;
      font-size: 11pt;
      line-height: 1.18;
      margin-bottom: 1.6mm;
    }}
    .toc-page .index-row {{
      font-size: 10.8pt;
      margin-bottom: 1.45mm;
    }}
    .index-row span:first-child {{
      text-align: left;
    }}
    .index-row span:last-child {{
      text-align: right;
      white-space: nowrap;
    }}
    .index-head {{
      font-weight: 700;
      margin-bottom: 2.4mm;
    }}
    @media print {{
      body {{
        background: white;
      }}
      .page {{
        margin: 0;
      }}
    }}
  </style>
</head>
<body>
{''.join(page_html)}
</body>
</html>
"""


def logo_data_uri() -> str:
    logo_path = Path(__file__).parent / "assets" / "uit_logo.jpeg"
    if not logo_path.exists():
        return ""
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def final_condensed_pages() -> list[list[tuple[str, int, str]]]:
    return [
        [
            page_number("39"),
            h("CHAPTER 7"),
            h("VERIFICATION AND VALIDATION"),
            p("Verification and validation ensure that the developed AI Study Assistant meets the stated requirements and works correctly under real usage conditions. The project was tested module by module and then as a complete Streamlit application."),
            sh("7.1 Testing Methodologies"),
            p("The testing process included unit testing, integration testing, system testing, and user workflow testing. Unit testing was used for PDF saving, text extraction, OCR decision logic, SQLite indexing, keyword retrieval, and quiz parsing. Integration testing was used to verify the complete flow from upload to answer generation."),
            p("The system was also tested using different document types: normal PDFs, image-only scanned PDFs, and handwritten notebook scans. This testing helped identify and fix the issue where scanner apps extracted only page numbers and the system incorrectly skipped OCR."),
            sh("7.2 Defect Analysis"),
            p("Important defects identified during development included slow first loading due to automatic embeddings, OCR skipping handwritten notes, generic Gemini errors, and retrieval mixing old PDF content. These were resolved using fast SQLite indexing, force OCR for handwritten pages, safer error handling, and source filtering."),
        ],
        [
            page_number("40"),
            sh("Testing Tables and Quality Factor Analysis"),
            p("Table: Unit Testing"),
            c("T1 PDF save function              Input PDF file                 File saved in uploads       Pass"),
            c("T2 PyPDF extraction               Text PDF                       Text extracted              Pass"),
            c("T3 Blank scanned PDF detection    Image-only PDF                 OCR triggered               Pass"),
            c("T4 Handwritten weak text check     Page number only               OCR triggered               Pass"),
            c("T5 SQLite index creation           Extracted chunks               Chunks stored               Pass"),
            c("T6 Keyword retrieval               Query terms                    Relevant chunks returned    Pass"),
            c("T7 Quiz parser                     JSON response                  Questions parsed            Pass"),
            p("Table: Quality Factor Analysis"),
            c("Correctness  : Answers are grounded in retrieved document chunks."),
            c("Reliability  : Retry and fallback logic handles temporary Gemini failures."),
            c("Efficiency   : SQLite keyword retrieval avoids slow embedding generation."),
            c("Integrity    : API keys are kept in .env or Streamlit secrets."),
            c("Portability  : The app can run locally or on Streamlit Community Cloud."),
            c("Usability    : Upload, chat, exam tools, OCR, and quiz mode are available in one UI."),
        ],
        [
            page_number("41"),
            h("CHAPTER 8"),
            h("CONCLUSION"),
            p("The AI Study Assistant using RAG successfully demonstrates how artificial intelligence can be applied to the education domain. The application enables students to upload PDF study material, process normal and scanned documents, ask questions, generate summaries, create MCQs, prepare viva questions, produce revision notes, and practice through interactive quiz mode."),
            p("The project implements a complete and practical pipeline consisting of PDF upload, text extraction, OCR, chunking, indexing, retrieval, and LLM-based response generation. The default SQLite keyword retrieval mode improves speed for demonstrations, while optional ChromaDB semantic search keeps the system extensible."),
            h("CHAPTER 9"),
            h("FUTURE WORK"),
            p("Future enhancements include student login, persistent chat history, downloadable study packs, subject-wise dashboards, voice input/output, cloud storage for uploaded documents, improved handwritten OCR, quiz analytics, and personalized learning recommendations."),
            h("CHAPTER 10"),
            h("REFERENCES"),
            b("Python, Streamlit, PyPDF, PyMuPDF, SQLite, ChromaDB, and Sentence Transformers documentation."),
            b("Google Gemini API documentation and model reference."),
            b("Research and online resources related to Retrieval-Augmented Generation, OCR, natural language processing, and educational AI systems."),
        ],
    ]


def main() -> None:
    root = Path(__file__).parent
    full_pages = build_pages()
    pages = full_pages[:9] + full_pages[9:47] + final_condensed_pages()
    markdown = build_markdown(pages)
    (root / "DETAILED_PROJECT_REPORT.md").write_text(markdown, encoding="utf-8")
    (root / "DETAILED_PROJECT_REPORT.html").write_text(
        build_html(pages),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
