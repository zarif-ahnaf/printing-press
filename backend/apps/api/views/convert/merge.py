from io import BytesIO

from django.http import HttpResponse
from ninja import File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile
from pypdf import PdfReader, PdfWriter

from ...http import HttpRequest

router = Router(tags=["PDF"])


@router.post("")
def merge_pdfs(
    request: HttpRequest,
    files: File[list[UploadedFile]],
):
    """
    Merge multiple uploaded PDF files into a single PDF.

    - Accepts 2 or more PDF files.
    - Returns merged PDF as an inline HTTP response.
    """
    if len(files) < 2:
        raise HttpError(400, "At least two PDF files are required.")

    writer = PdfWriter()

    for uploaded_file in files:
        # Safely get the filename
        filename = getattr(uploaded_file, "name", None)
        if not filename or not isinstance(filename, str):
            raise HttpError(400, "Uploaded file is missing a valid filename.")
        if not filename.lower().endswith(".pdf"):
            raise HttpError(400, f"File '{filename}' is not a PDF.")

        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            writer.add_page(page)

    # Optional: ensure at least one page was added (pypdf will handle empty, but good to check)
    if len(writer.pages) == 0:
        raise HttpError(400, "No pages found in the provided PDF files.")

    # Write to in-memory buffer
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="merged.pdf"'
    return response
