from django.http import HttpResponse
from ninja import Router
from ninja.files import UploadedFile
import fitz  # PyMuPDF

router = Router(tags=["PDF"])


@router.post("", response=None)
def merge_pdfs(request, files: list[UploadedFile]):
    merged_doc = fitz.open()

    try:
        for file in files:
            # Read uploaded file into memory
            file_bytes = file.read()

            if len(file_bytes) < 4:
                return HttpResponse("File is too small to be a PDF.", status=400)

            # Check PDF magic bytes
            if not file_bytes.startswith(b"%PDF-"):
                return HttpResponse(
                    f"File '{file.name or 'unnamed'}' is not a valid PDF.", status=400
                )

            # Open PDF from bytes
            try:
                src_doc = fitz.open("pdf", file_bytes)
            except Exception as e:
                return HttpResponse(
                    f"Invalid PDF '{file.name or 'unnamed'}': {str(e)}", status=400
                )

            # Append all pages from this PDF
            merged_doc.insert_pdf(src_doc)
            src_doc.close()

        # Output merged PDF as bytes
        merged_bytes = merged_doc.tobytes()

    finally:
        merged_doc.close()

    response = HttpResponse(merged_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="merged.pdf"'
    return response
