from io import BytesIO
import base64
import hashlib
import os
from pathlib import Path
import re
import time
from typing import NamedTuple
import shutil

from pypdf import PdfReader
import requests


class PdfPage(NamedTuple):
    page_number: int
    text: str
    extraction_method: str = "text"


def save_uploaded_file(uploaded_file, upload_dir: Path) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    destination = upload_dir / safe_name

    with destination.open("wb") as file:
        file.write(uploaded_file.getbuffer())

    return destination


def extract_pdf_pages(
    pdf_path: Path,
    use_ocr: bool = True,
    ocr_mode: str = "printed",
    force_ocr: bool = False,
) -> list[PdfPage]:
    reader = PdfReader(str(pdf_path))
    pages: list[PdfPage] = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        cleaned = " ".join(text.split())
        should_ocr = use_ocr and (
            force_ocr or _should_ocr_page(cleaned, ocr_mode=ocr_mode)
        )

        if should_ocr:
            ocr_text = extract_page_text_with_ocr(pdf_path, index - 1, ocr_mode=ocr_mode)
            if ocr_text:
                pages.append(
                    PdfPage(
                        page_number=index,
                        text=ocr_text,
                        extraction_method="ocr",
                    )
                )
            elif cleaned:
                pages.append(PdfPage(page_number=index, text=cleaned))
        elif cleaned:
            pages.append(PdfPage(page_number=index, text=cleaned))

    return pages


def extract_page_text_with_ocr(
    pdf_path: Path,
    page_index: int,
    ocr_mode: str = "printed",
) -> str:
    provider = os.getenv("OCR_PROVIDER", "auto").lower().strip()

    if provider == "local":
        return extract_page_text_with_local_ocr(pdf_path, page_index, ocr_mode=ocr_mode)
    if provider == "gemini":
        return extract_page_text_with_gemini_ocr(pdf_path, page_index, ocr_mode=ocr_mode)
    if provider != "auto":
        raise RuntimeError("OCR_PROVIDER must be auto, gemini, or local.")

    if _local_ocr_available():
        return extract_page_text_with_local_ocr(pdf_path, page_index, ocr_mode=ocr_mode)

    try:
        return extract_page_text_with_gemini_ocr(pdf_path, page_index, ocr_mode=ocr_mode)
    except RuntimeError as exc:
        raise RuntimeError(
            f"{exc} Local OCR is not installed. Install Tesseract OCR and "
            "pytesseract, or set OCR_PROVIDER=gemini after fixing internet/DNS."
        ) from exc


def extract_page_text_with_local_ocr(
    pdf_path: Path,
    page_index: int,
    ocr_mode: str = "printed",
) -> str:
    cache_path = _ocr_cache_path(pdf_path, page_index, provider="local", ocr_mode=ocr_mode)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    if not _local_ocr_available():
        raise RuntimeError(
            "Local OCR is not available. Install Tesseract OCR and pytesseract, "
            "then set OCR_PROVIDER=local or OCR_PROVIDER=auto."
        )

    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF, Pillow, and pytesseract for local OCR.") from exc

    command = os.getenv("TESSERACT_CMD")
    if command:
        pytesseract.pytesseract.tesseract_cmd = command

    image = _render_pdf_page_image(pdf_path, page_index, ocr_mode=ocr_mode)

    language = os.getenv("TESSERACT_LANG", "eng")
    text = pytesseract.image_to_string(image, lang=language)
    cleaned = " ".join(text.split())
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(cleaned, encoding="utf-8")
    return cleaned


def extract_page_text_with_gemini_ocr(
    pdf_path: Path,
    page_index: int,
    ocr_mode: str = "printed",
) -> str:
    cache_path = _ocr_cache_path(pdf_path, page_index, provider="gemini", ocr_mode=ocr_mode)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY in .env to OCR scanned PDF pages.")

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "Install PyMuPDF to OCR scanned PDFs."
        ) from exc

    image = _render_pdf_page_image(pdf_path, page_index, ocr_mode=ocr_mode)
    output = BytesIO()
    image.save(output, format="PNG")
    image_bytes = output.getvalue()

    model_names = _gemini_model_candidates(
        primary=os.getenv(
            "GEMINI_OCR_MODEL",
            os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        ),
        fallbacks=os.getenv(
            "GEMINI_OCR_FALLBACK_MODELS",
            "gemini-flash-latest,gemini-3.1-flash-lite",
        ),
    )
    timeout = int(os.getenv("GEMINI_OCR_TIMEOUT", "45"))
    retries = int(os.getenv("GEMINI_OCR_RETRIES", "3"))

    response = _generate_ocr_with_fallbacks(
        api_key=api_key,
        model_names=model_names,
        image_bytes=image_bytes,
        ocr_mode=ocr_mode,
        timeout=timeout,
        retries=retries,
    )
    payload = response.json()
    text = _extract_gemini_text(payload)
    cleaned = " ".join(text.split())
    if cleaned.lower() in {"empty", "empty response", "no readable text", "nothing"}:
        cleaned = ""

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(cleaned, encoding="utf-8")
    return cleaned


def _generate_ocr_with_fallbacks(
    api_key: str,
    model_names: list[str],
    image_bytes: bytes,
    ocr_mode: str,
    timeout: int,
    retries: int,
) -> requests.Response:
    errors: list[str] = []

    for model_name in model_names:
        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                    headers={"x-goog-api-key": api_key},
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": _ocr_prompt(ocr_mode)
                                    },
                                    {
                                        "inline_data": {
                                            "mime_type": "image/png",
                                            "data": base64.b64encode(image_bytes).decode("ascii"),
                                        }
                                    },
                                ]
                            }
                        ],
                        "generationConfig": {
                            "temperature": 0,
                            "maxOutputTokens": 4096,
                        },
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                detail = _safe_request_error(exc)
                errors.append(f"{model_name}: {detail}")

                status = getattr(getattr(exc, "response", None), "status_code", None)
                should_retry = status in {429, 500, 502, 503, 504} or status is None
                if should_retry and attempt < retries:
                    time.sleep(min(2 ** (attempt - 1), 6))
                    continue
                break

    raise RuntimeError(
        _summarize_ocr_errors(errors)
    )


def _extract_gemini_text(payload: dict) -> str:
    parts = (
        payload.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    return " ".join(part.get("text", "") for part in parts)


def _safe_request_error(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        raw = str(exc).split("?key=")[0]
        if "NameResolutionError" in raw or "getaddrinfo failed" in raw:
            return "DNS lookup failed for generativelanguage.googleapis.com"
        return raw[:300]

    status = response.status_code
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message", response.text)
    except ValueError:
        message = response.text

    return f"HTTP {status} - {message[:300]}"


def _gemini_model_candidates(primary: str, fallbacks: str) -> list[str]:
    candidates: list[str] = []
    for model_name in [primary, *fallbacks.split(",")]:
        cleaned = model_name.strip()
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    return candidates


def _render_pdf_page_image(pdf_path: Path, page_index: int, ocr_mode: str):
    try:
        import fitz
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF and Pillow for OCR rendering.") from exc

    default_scale = "2.4" if ocr_mode == "handwritten" else "1.4"
    scale = float(os.getenv("HANDWRITING_OCR_RENDER_SCALE" if ocr_mode == "handwritten" else "OCR_RENDER_SCALE", default_scale))

    with fitz.open(str(pdf_path)) as document:
        page = document.load_page(page_index)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")

    if ocr_mode == "handwritten":
        image = ImageOps.grayscale(image)
        image = ImageOps.autocontrast(image)
        image = ImageEnhance.Contrast(image).enhance(1.8)
        image = ImageEnhance.Sharpness(image).enhance(1.5)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        image = image.convert("RGB")

    return image


def _ocr_prompt(ocr_mode: str) -> str:
    if ocr_mode == "handwritten":
        return (
            "You are reading a photographed/scanned handwritten study-notes page. "
            "Carefully transcribe all readable handwritten text. Return only the "
            "transcribed notes, not commentary. Preserve headings, bullet points, "
            "numbering, dates, formulas, diagrams labels, and short forms where possible. "
            "If a word is unclear, write [unclear] instead of guessing. If the page "
            "contains mixed printed and handwritten text, include both. Keep line order "
            "as close to the original page as possible."
        )

    return (
        "Extract all readable text from this scanned PDF page. Return only the "
        "extracted text. Preserve headings, lists, dates, names, numbers, "
        "definitions, formulas, and question numbers where possible. If there is "
        "no readable text, return nothing."
    )


def _should_ocr_page(cleaned_text: str, ocr_mode: str) -> bool:
    if not cleaned_text:
        return True

    if ocr_mode != "handwritten":
        return False

    # Scanner apps often add only page numbers or tiny metadata. That text is
    # technically extractable, but useless for notes, so handwritten mode should
    # still OCR the image.
    if len(cleaned_text) < 30:
        return True

    words = re.findall(r"[A-Za-z]{3,}", cleaned_text)
    if len(words) < 3:
        return True

    return False


def _local_ocr_available() -> bool:
    if os.getenv("TESSERACT_CMD"):
        return True
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return True


def _summarize_ocr_errors(errors: list[str]) -> str:
    if any("DNS lookup failed" in error for error in errors):
        return (
            "Gemini OCR could not connect because DNS lookup failed for "
            "generativelanguage.googleapis.com. Check internet/DNS/VPN/firewall, "
            "or install local OCR with Tesseract."
        )

    return (
        "Gemini OCR request failed after retries/fallbacks: "
        + " | ".join(errors[-3:])
        + ". Try again later, or change GEMINI_OCR_MODEL / GEMINI_OCR_FALLBACK_MODELS."
    )


def _ocr_cache_path(
    pdf_path: Path,
    page_index: int,
    provider: str,
    ocr_mode: str,
) -> Path:
    stat = pdf_path.stat()
    raw = (
        f"{provider}:{ocr_mode}:{pdf_path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:{page_index}"
    ).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return pdf_path.parent / ".ocr_cache" / f"{digest}.txt"
