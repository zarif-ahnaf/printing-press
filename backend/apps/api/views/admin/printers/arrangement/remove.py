from django.shortcuts import get_object_or_404
from ninja import Router

from apps.printers.models import PrinterArrangements

from .....decorators import admin_required
from .....http import HttpRequest
from .....schemas.printer_arrangement import (
    PrinterArrangementDeleteSchema,
)

router = Router(tags=["Admin Printer Arrangements"])


@router.delete("{id}", response=PrinterArrangementDeleteSchema)
@admin_required
def printer_arrangements_remove(
    request: HttpRequest,
    id: int,
):
    printer_arrangement = get_object_or_404(PrinterArrangements, id=id)
    printer_arrangement.delete()
    return PrinterArrangementDeleteSchema(
        id=id,
        message="Printer arrangement has been removed successfully.",
    )
