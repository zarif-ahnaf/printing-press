from ninja import Router, File
from ninja.files import UploadedFile
from django.http import HttpResponse
import tempfile
from pathlib import Path
from ....utils.docx import doc2pdf
from ....http import HttpRequest

router = Router(tags=["PDF"])


@router.post("/convert")
def convert_docx_to_pdf_endpoint(request: HttpRequest, file: File[UploadedFile]):
    # Use a default filename if none is provided
    filename = file.name or "temp.docx"

    with tempfile.TemporaryDirectory() as temp_dir:
        # Save uploaded file to temp directory
        input_path = Path(temp_dir) / filename
        with open(input_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        # Convert using loutils
        doc2pdf(input_path)

        # Read the generated PDF
        pdf_path = input_path.with_suffix(".pdf")
        if not pdf_path.exists():
            return {"error": "PDF conversion failed"}

        with open(pdf_path, "rb") as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="{input_path.stem}.pdf"'
            )
            return response
