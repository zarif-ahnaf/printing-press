from ninja import Router

from apps.printers.models import PrinterArrangements

from .....decorators import admin_required
from .....http import HttpRequest
from .....schemas.printer_arrangement import (
    PrinterArrangementCreateSchema,
    PrinterArrangementOutSchema,
)

router = Router(tags=["Admin Printer Arrangements"])


@router.post("", response=PrinterArrangementOutSchema)
@admin_required
def printer_arrangements_add(
    request: HttpRequest,
    payload: PrinterArrangementCreateSchema,
):
    arrangement = PrinterArrangements.objects.create(
        color_printer__id=payload.color_printer,
        black_and_white_printer__id=payload.black_and_white_printer,
    )
    return arrangement
