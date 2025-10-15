from ninja.files import UploadedFile
import fitz
from typing import Optional


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
