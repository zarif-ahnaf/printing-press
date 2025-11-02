from django.shortcuts import get_object_or_404
from ninja import Router

from apps.printers.models import Printers

from ....decorators import admin_required
from ....http import HttpRequest
from ....schemas.printer import PrinterDeleteSchema
from ....auth import AuthBearer

router = Router(tags=["Admin Printers"])


@router.post("{id}", auth=AuthBearer(), response=PrinterDeleteSchema)
@admin_required
def printer_remove(request: HttpRequest, id: int):
    printer = get_object_or_404(Printers, id=id)
    printer.delete()
    return PrinterDeleteSchema(id=id, message="Printer removed successfully.")
