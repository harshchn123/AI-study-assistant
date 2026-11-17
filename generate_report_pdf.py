from datetime import date
from pathlib import Path
import re
import textwrap


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 58
MARGIN_TOP = 64
MARGIN_BOTTOM = 56
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN_X)

NAVY = (25, 48, 78)
BLUE = (33, 104, 172)
LIGHT_BLUE = (230, 240, 250)
PALE_GRAY = (246, 248, 250)
DARK_GRAY = (60, 64, 67)
MID_GRAY = (120, 126, 134)
WHITE = (1, 1, 1)
BLACK = (0, 0, 0)


def pdf_escape(text: str) -> str:
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("cp1252", errors="replace").decode("cp1252")


def rgb(color: tuple[float, float, float]) -> tuple[float, float, float]:
    if max(color) <= 1:
        return color
    return tuple(value / 255 for value in color)


def text_width(text: str, font_size: int) -> float:
    return len(text) * font_size * 0.48


def wrap_text(text: str, font_size: int, max_width: int) -> list[str]:
    if not text:
        return [""]

    avg_char_width = max(font_size * 0.48, 1)
    width_chars = max(int(max_width / avg_char_width), 20)
    wrapped: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            wrapped.append("")
            continue
        wrapped.extend(
            textwrap.wrap(
                line,
                width=width_chars,
                replace_whitespace=True,
                drop_whitespace=True,
            )
        )
    return wrapped


def parse_markdown(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    in_code = False
    code_lines: list[str] = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            if in_code:
                blocks.append({"type": "code", "text": "\n".join(code_lines)})
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            blocks.append({"type": "space"})
        elif line.startswith("# "):
            blocks.append({"type": "title", "text": line[2:].strip()})
        elif line.startswith("## "):
            blocks.append({"type": "heading", "text": line[3:].strip()})
        elif line.startswith("- "):
            blocks.append({"type": "bullet", "text": line[2:].strip()})
        elif re.match(r"^\d+\.\s+", line):
            blocks.append({"type": "numbered", "text": line.strip()})
        else:
            blocks.append({"type": "paragraph", "text": line.strip()})

    if code_lines:
        blocks.append({"type": "code", "text": "\n".join(code_lines)})

    return blocks


class PdfReport:
    def __init__(self) -> None:
        self.pages: list[list[str]] = []
        self.current: list[str] = []
        self.y = PAGE_HEIGHT - MARGIN_TOP
        self.page_number = 0

    def begin_page(self, decorated: bool = True) -> None:
        if self.current:
            if self.page_number > 1:
                self._footer()
            self.pages.append(self.current)
        self.page_number += 1
        self.current = []
        self.y = PAGE_HEIGHT - MARGIN_TOP
        if decorated:
            self._header()

    def _header(self) -> None:
        self.draw_text(
            "AI Study Assistant using RAG",
            MARGIN_X,
            PAGE_HEIGHT - 30,
            9,
            "F2",
            color=NAVY,
        )
        self.draw_text(
            "Project Report",
            PAGE_WIDTH - MARGIN_X - 72,
            PAGE_HEIGHT - 30,
            9,
            "F1",
            color=MID_GRAY,
        )
        self.draw_line(MARGIN_X, PAGE_HEIGHT - 42, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 42, color=LIGHT_BLUE)

    def _footer(self) -> None:
        self.draw_line(MARGIN_X, 40, PAGE_WIDTH - MARGIN_X, 40, color=LIGHT_BLUE)
        self.draw_text(f"Page {self.page_number}", PAGE_WIDTH - MARGIN_X - 42, 25, 9, "F1", color=MID_GRAY)

    def ensure_space(self, height: float) -> None:
        if self.y - height < MARGIN_BOTTOM:
            self.begin_page()

    def set_fill(self, color: tuple[float, float, float]) -> str:
        r, g, b = rgb(color)
        return f"{r:.3f} {g:.3f} {b:.3f} rg"

    def set_stroke(self, color: tuple[float, float, float]) -> str:
        r, g, b = rgb(color)
        return f"{r:.3f} {g:.3f} {b:.3f} RG"

    def draw_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[float, float, float] = BLACK,
        width: float = 0.8,
    ) -> None:
        self.current.append(f"{self.set_stroke(color)} {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def draw_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: tuple[float, float, float] | None = None,
        stroke: tuple[float, float, float] | None = None,
    ) -> None:
        parts = []
        if fill:
            parts.append(self.set_fill(fill))
        if stroke:
            parts.append(self.set_stroke(stroke))
        parts.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re")
        parts.append("B" if fill and stroke else "f" if fill else "S")
        self.current.append(" ".join(parts))

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        size: int,
        font: str = "F1",
        color: tuple[float, float, float] = BLACK,
    ) -> None:
        escaped = pdf_escape(text)
        self.current.append(f"{self.set_fill(color)} BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({escaped}) Tj ET")

    def add_cover_page(self) -> None:
        self.begin_page(decorated=False)
        self.draw_rect(0, PAGE_HEIGHT - 190, PAGE_WIDTH, 190, fill=NAVY)
        self.draw_rect(0, PAGE_HEIGHT - 196, PAGE_WIDTH, 6, fill=BLUE)
        self.draw_text("PROJECT REPORT", MARGIN_X, PAGE_HEIGHT - 92, 14, "F2", color=LIGHT_BLUE)
        self.draw_text("AI Study Assistant", MARGIN_X, PAGE_HEIGHT - 132, 30, "F2", color=WHITE)
        self.draw_text("using Retrieval-Augmented Generation", MARGIN_X, PAGE_HEIGHT - 160, 17, "F1", color=WHITE)

        self.draw_rect(MARGIN_X, PAGE_HEIGHT - 360, CONTENT_WIDTH, 112, fill=PALE_GRAY, stroke=LIGHT_BLUE)
        self.draw_text("Project Domain", MARGIN_X + 22, PAGE_HEIGHT - 282, 10, "F2", color=MID_GRAY)
        self.draw_text("Artificial Intelligence and Education Technology", MARGIN_X + 22, PAGE_HEIGHT - 304, 14, "F2", color=NAVY)
        self.draw_text("Technology Stack", MARGIN_X + 22, PAGE_HEIGHT - 334, 10, "F2", color=MID_GRAY)
        self.draw_text("Python, Streamlit, LangChain, ChromaDB, Sentence Transformers, LLM APIs", MARGIN_X + 22, PAGE_HEIGHT - 354, 11, "F1", color=DARK_GRAY)

        start_y = PAGE_HEIGHT - 445
        details = [
            ("Submitted By", "Aryan Sharma (Roll No. 16222990012)"),
            ("Department", "Information Technology"),
            ("Academic Year", "2022 - 2026"),
            ("Prepared On", "29 June 2026"),
        ]
        for index, (label, value) in enumerate(details):
            y = start_y - index * 34
            self.draw_text(label, MARGIN_X, y, 10, "F2", color=MID_GRAY)
            self.draw_line(MARGIN_X + 105, y - 2, PAGE_WIDTH - MARGIN_X, y - 2, color=LIGHT_BLUE)
            self.draw_text(value, MARGIN_X + 112, y, 11, "F1", color=DARK_GRAY)

    def add_table_of_contents(self, headings: list[str]) -> None:
        self.begin_page()
        self.draw_text("Table of Contents", MARGIN_X, self.y, 22, "F2", color=NAVY)
        self.y -= 34
        for heading in headings:
            self.ensure_space(22)
            self.draw_text(heading, MARGIN_X + 8, self.y, 11, "F1", color=DARK_GRAY)
            self.draw_line(MARGIN_X, self.y - 8, PAGE_WIDTH - MARGIN_X, self.y - 8, color=PALE_GRAY)
            self.y -= 22

    def add_wrapped(
        self,
        text: str,
        font_size: int = 10,
        font: str = "F1",
        indent: int = 0,
        spacing_before: int = 0,
        spacing_after: int = 7,
        bullet_prefix: str | None = None,
        color: tuple[float, float, float] = DARK_GRAY,
    ) -> None:
        max_width = CONTENT_WIDTH - indent
        lines = wrap_text(text, font_size, max_width)
        line_height = font_size * 1.42
        total_height = spacing_before + (len(lines) * line_height) + spacing_after
        self.ensure_space(total_height)
        self.y -= spacing_before

        for index, line in enumerate(lines):
            prefix = bullet_prefix if index == 0 and bullet_prefix else ""
            self.draw_text(f"{prefix}{line}", MARGIN_X + indent, self.y, font_size, font, color=color)
            self.y -= line_height

        self.y -= spacing_after

    def add_heading(self, text: str) -> None:
        self.ensure_space(54)
        self.y -= 10
        self.draw_rect(MARGIN_X, self.y - 8, 5, 22, fill=BLUE)
        self.draw_text(text, MARGIN_X + 14, self.y, 15, "F2", color=NAVY)
        self.y -= 22
        self.draw_line(MARGIN_X + 14, self.y, PAGE_WIDTH - MARGIN_X, self.y, color=LIGHT_BLUE)
        self.y -= 14

    def add_code_block(self, text: str) -> None:
        lines = text.splitlines() or [""]
        font_size = 8
        line_height = 11
        height = len(lines) * line_height + 16
        self.ensure_space(height + 12)
        self.draw_rect(MARGIN_X, self.y - height + 8, CONTENT_WIDTH, height, fill=PALE_GRAY, stroke=LIGHT_BLUE)
        y = self.y - 8
        for line in lines:
            clipped = line[:95]
            self.draw_text(clipped, MARGIN_X + 12, y, font_size, "F3", color=DARK_GRAY)
            y -= line_height
        self.y -= height + 10

    def add_space(self) -> None:
        self.y -= 3
        if self.y < MARGIN_BOTTOM:
            self.begin_page()

    def finish(self) -> None:
        if self.current:
            self._footer()
            self.pages.append(self.current)
            self.current = []

    def write(self, path: Path) -> None:
        self.finish()
        objects: list[bytes] = []

        def add_object(body: str | bytes) -> int:
            if isinstance(body, str):
                body = body.encode("cp1252", errors="replace")
            objects.append(body)
            return len(objects)

        font_regular = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        font_bold = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        font_mono = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        page_object_ids: list[int] = []
        content_object_ids: list[int] = []

        for page in self.pages:
            stream = "\n".join(page).encode("cp1252", errors="replace")
            content_id = add_object(
                b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
                + stream
                + b"\nendstream"
            )
            content_object_ids.append(content_id)
            page_object_ids.append(0)

        pages_id = len(objects) + len(page_object_ids) + 1

        for index, content_id in enumerate(content_object_ids):
            page_id = add_object(
                "<< /Type /Page "
                f"/Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R /F3 {font_mono} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
            page_object_ids[index] = page_id

        kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
        pages_id = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>")
        catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for object_id, body in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
            pdf.extend(body)
            pdf.extend(b"\nendobj\n")

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            (
                "trailer\n"
                f"<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
                "startxref\n"
                f"{xref_offset}\n"
                "%%EOF\n"
            ).encode("ascii")
        )
        path.write_bytes(pdf)


def report_headings(blocks: list[dict]) -> list[str]:
    return [
        block["text"]
        for block in blocks
        if block["type"] == "heading" and block["text"] != "AI Study Assistant using RAG"
    ]


def main() -> None:
    root = Path(__file__).parent
    markdown = (root / "PROJECT_REPORT.md").read_text(encoding="utf-8")
    blocks = parse_markdown(markdown)
    report = PdfReport()

    report.add_cover_page()
    report.add_table_of_contents(report_headings(blocks))
    report.begin_page()

    for block in blocks:
        block_type = block["type"]
        text = block.get("text", "")

        if block_type == "title" or text == "AI Study Assistant using RAG":
            continue
        if block_type == "heading":
            report.add_heading(text)
        elif block_type == "bullet":
            report.add_wrapped(text, font_size=10, indent=18, bullet_prefix="- ")
        elif block_type == "numbered":
            report.add_wrapped(text, font_size=10, indent=12)
        elif block_type == "code":
            report.add_code_block(text)
        elif block_type == "space":
            report.add_space()
        else:
            report.add_wrapped(text, font_size=10)

    report.write(root / "PROJECT_REPORT.pdf")


if __name__ == "__main__":
    main()
