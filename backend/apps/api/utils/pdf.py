import io
from io import BytesIO
from typing import Optional

import fitz
import pypdfium2 as pdfium
from ninja.files import UploadedFile
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError


def extract_non_blank_pages(doc: fitz.Document, text_threshold: int = 10) -> list[int]:
    """
    Analyze a PDF document and return indices of non-blank pages.
    A page is non-blank if it has > `text_threshold` chars or contains images.
    """
    non_blank_indices = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        images = page.get_images(full=True)

        if len(text) > text_threshold or len(images) > 0:
            non_blank_indices.append(page_num)
    return non_blank_indices


def generate_summary(filename: str, total_pages: int, non_blank_pages: int) -> dict:
    """Generate the JSON summary response."""
    blank_pages = total_pages - non_blank_pages
    return {
        "filename": filename,
        "total_pages": total_pages,
        "non_blank_pages": non_blank_pages,
        "blank_pages": blank_pages,
    }


def generate_filtered_pdf(doc: fitz.Document, non_blank_indices: list[int]) -> bytes:
    """Create a new PDF containing only the specified page indices."""
    new_doc = fitz.open()
    try:
        for idx in non_blank_indices:
            new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        return new_doc.tobytes()
    finally:
        new_doc.close()


def process_pdf_file(
    uploaded_file: UploadedFile, return_pdf: bool = False, text_threshold: int = 10
) -> tuple[dict, Optional[bytes]]:
    """
    End-to-end PDF processing service.
    Returns summary dict and optional filtered PDF bytes.
    """
    file_bytes = uploaded_file.read()
    doc = fitz.open("pdf", file_bytes)

    try:
        total_pages = doc.page_count
        non_blank_indices = extract_non_blank_pages(doc, text_threshold)
        non_blank_count = len(non_blank_indices)

        safe_filename = uploaded_file.name or "unknown"
        summary = generate_summary(
            filename=safe_filename,
            total_pages=total_pages,
            non_blank_pages=non_blank_count,
        )

        filtered_pdf_bytes = None
        if return_pdf:
            filtered_pdf_bytes = generate_filtered_pdf(doc, non_blank_indices)

        return summary, filtered_pdf_bytes

    finally:
        if not doc.is_closed:
            doc.close()


def count_pdf_pages(pdf_bytes: bytes) -> int:
    """
    Count pages in a PDF from raw bytes using pypdf.
    Raises ValueError on invalid/encrypted/corrupted PDFs.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("Encrypted PDFs are not allowed.")
        return len(reader.pages)
    except (PdfReadError, ValueError, OSError, TypeError) as e:
        raise ValueError(f"Invalid or corrupted PDF: {str(e)}")


def _is_color_page(pil_img, tolerance: int = 5) -> bool:
    if pil_img.mode in ("L", "1"):
        return False
    hsv = pil_img.convert("HSV")
    _, s, _ = hsv.split()
    return max(s.getdata()) > tolerance


def split_pdf_into_colored_pages(
    pdf_bytes: bytes, dpi: int = 75, tolerance: int = 5
) -> bytes:
    """Return PDF with ONLY color pages (highly compressed)."""
    src_render = pdfium.PdfDocument(pdf_bytes)
    src_copy = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    scale = dpi / 72.0
    for i in range(len(src_render)):
        bitmap = src_render[i].render(scale=scale)
        pil_img = bitmap.to_pil()
        if _is_color_page(pil_img, tolerance):
            writer.add_page(src_copy.pages[i])
        src_render[i].close()
    src_render.close()

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def split_pdf_into_black_and_white_pages(
    pdf_bytes: bytes, dpi: int = 75, tolerance: int = 5
) -> bytes:
    """Return PDF with ONLY grayscale pages (highly compressed)."""
    src_render = pdfium.PdfDocument(pdf_bytes)
    src_copy = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    scale = dpi / 72.0
    for i in range(len(src_render)):
        bitmap = src_render[i].render(scale=scale)
        pil_img = bitmap.to_pil()
        if not _is_color_page(pil_img, tolerance):
            writer.add_page(src_copy.pages[i])
        src_render[i].close()
    src_render.close()

    output = BytesIO()
    writer.write(output)
    return output.getvalue()
