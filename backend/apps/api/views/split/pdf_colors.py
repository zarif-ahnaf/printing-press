from django.http import HttpResponse
from ninja import File, Router, UploadedFile

from ...http import HttpRequest
from ...utils.pdf import (
    split_pdf_into_black_and_white_pages,
    split_pdf_into_colored_pages,
)

router = Router(tags=["PDF"])


@router.post("/color/")
def split_color(request: HttpRequest, file: File[UploadedFile]):
    pdf_bytes = file.read()
    color_pdf = split_pdf_into_colored_pages(pdf_bytes)
    response = HttpResponse(color_pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="color.pdf"'
    return response


@router.post("/grayscale/")
def split_grayscale(request: HttpRequest, file: File[UploadedFile]):
    pdf_bytes = file.read()
    gray_pdf = split_pdf_into_black_and_white_pages(pdf_bytes)
    response = HttpResponse(gray_pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="grayscale.pdf"'
    return response
