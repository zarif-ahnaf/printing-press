from ninja import Router

from apps.printers.models import PrinterArrangements

from ....http import HttpRequest
from ....schemas.printer_arrangement import (
    PrinterArrangementOutSchema,
)

router = Router(tags=["Printer Arrangements"])


@router.get("", response=list[PrinterArrangementOutSchema])
def list_printer_arrangements(
    request: HttpRequest,
):
    printer_arrangement = PrinterArrangements.objects.all()
    return printer_arrangement
