from ninja import File, Form, Router, UploadedFile

from apps.printers.models import Printers

from .....auth import AuthBearer
from .....decorators import admin_required
from .....http import HttpRequest
from .....schemas.printer import PrinterCreateSchema, PrinterOutSchema

router = Router(tags=["Admin Printers"])


@router.post("/", auth=AuthBearer(), response=PrinterOutSchema)
@admin_required
def printers_add(
    request: HttpRequest,
    payload: Form[PrinterCreateSchema],
    image: File[UploadedFile],
):
    data = Printers.objects.create(
        name=payload.name,
        image=image,
        is_color=payload.is_color,
        simplex_charge=payload.simplex_charge,
        duplex_charge=payload.duplex_charge,
    )
    return data
