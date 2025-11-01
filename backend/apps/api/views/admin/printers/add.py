from ninja import File, Router, UploadedFile

from apps.printers.models import Printers

from ....decorators import admin_required
from ....schemas.printer import PrinterCreateSchema

router = Router(tags=["Admin Printers"])


@router.post("", response=PrinterCreateSchema)
@admin_required
def printers_add(request, image: File[UploadedFile], payload: PrinterCreateSchema):
    data = Printers.objects.create(
        name=payload.name,
        image=image,
        is_color=payload.is_color,
        simplex_charge=payload.simplex_charge,
        duplex_charge=payload.duplex_charge,
    )
    return data
