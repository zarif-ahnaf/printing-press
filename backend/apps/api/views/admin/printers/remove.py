from django.shortcuts import get_object_or_404
from ninja import Router

from apps.printers.models import Printers

from ....decorators import admin_required
from ....schemas.printer import PrinterDeleteSchema

router = Router(tags=["Admin Printers"])


@router.post("{id}/", response=PrinterDeleteSchema)
@admin_required
def printer_remove(request, id: int):
    printer = get_object_or_404(Printers, id=id)
    printer.delete()
    return PrinterDeleteSchema(id=id, message="Printer removed successfully.")
