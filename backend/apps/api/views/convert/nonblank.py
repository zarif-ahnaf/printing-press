from django.http import Http404, HttpResponse
from ninja import File, Form, Router
from ninja.files import UploadedFile

from ...http import HttpRequest
from ...utils.pdf import process_pdf_file

router = Router(tags=["PDF"])


@router.post("")
def count_nonblank_pages(
    request: HttpRequest,
    file: File[UploadedFile],
    return_pdf: Form[bool] = False,
):
    """
    Upload a PDF to count non-blank pages.
    Set `return_pdf=true` to download a version without blank pages.
    """
    try:
        summary, pdf_bytes = process_pdf_file(
            uploaded_file=file, return_pdf=return_pdf, text_threshold=10
        )
    except Exception as e:
        # In production, log the error and return a user-friendly message
        raise Http404("Failed to process PDF. Ensure it's a valid PDF file.") from e

    if return_pdf and pdf_bytes is not None:
        safe_name = (
            (getattr(file, "name", None) or "uploaded.pdf")
            .replace("/", "_")
            .replace("\\", "_")
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="nonblank_{safe_name}"'
        return response

    return summary
