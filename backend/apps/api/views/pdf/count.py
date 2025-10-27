import io

from django.http import HttpResponse
from ninja import File, Router, Schema
from ninja.files import UploadedFile
from pypdf import PdfReader

router = Router(tags=["PDF"])


class PDFPageCountOut(Schema):
    page_count: int
    filename: str


@router.post("", response=PDFPageCountOut)
def get_pdf_page_count(request, file: File[UploadedFile]):
    """
    Upload a PDF and get its page count.
    """
    # Handle missing or invalid filename
    filename = file.name if file.name else "unnamed.pdf"

    if not filename.lower().endswith(".pdf"):
        return HttpResponse("Only PDF files are allowed.", status=400)

    try:
        file_bytes = file.read()
        reader = PdfReader(io.BytesIO(file_bytes))
        page_count = len(reader.pages)

        return PDFPageCountOut(page_count=page_count, filename=filename)
    except Exception as e:
        return HttpResponse(f"Failed to process PDF: {str(e)}", status=400)
