import tempfile
from pathlib import Path

from django.http import HttpResponse
from ninja import File, Router
from ninja.files import UploadedFile

from ...http import HttpRequest
from ...utils.docx import doc2pdf

router = Router(tags=["PDF"])


@router.post("")
def convert_to_pdf(request: HttpRequest, file: File[UploadedFile]):
    filename = file.name or "temp.docx"
    stem = Path(filename).stem

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / filename
        output_path = input_path.with_suffix(".pdf")

        with open(input_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        # Convert DOCX → PDF (this likely requires a real file)
        doc2pdf(input_path)

        # Check if PDF was created
        if not output_path.exists():
            return {"error": "PDF conversion failed"}

        # Read PDF and return as response
        with open(output_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

    # TemporaryDirectory is now cleaned up (files deleted)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{stem}.pdf"'
    return response
