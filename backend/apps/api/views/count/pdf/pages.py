from ninja import File, Router, UploadedFile
from ninja.errors import HttpError

from ....schemas.count import PageCountResponse
from ....utils.pdf import count_pdf_pages

router = Router(tags=["PDF"])


@router.post("/count-pages", response=PageCountResponse)
def count_pages(request, file: File[UploadedFile]) -> PageCountResponse:
    """
    Count the number of pages in an uploaded PDF file.
    Rejects encrypted, corrupted, or invalid PDFs.
    """
    file_bytes = file.read()
    try:
        page_count = count_pdf_pages(file_bytes)
        return PageCountResponse(page_count=page_count)
    except ValueError as e:
        raise HttpError(400, str(e))
