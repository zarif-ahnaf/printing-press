from ninja import Router

from apps.printers.models import PrinterArrangements

from ....schemas.printer_arrangement import (
    PrinterArrangementOutSchema,
)

router = Router(tags=["Printer Arrangements"])


@router.get("", response=list[PrinterArrangementOutSchema])
def list_arrangements(request):
    arrangements = PrinterArrangements.objects.all()
    return [
        {
            "id": arr.pk,
            "decomissioned": arr.decomissioned,
            "color_printer": arr.color_printer.id if arr.color_printer else None,
            "bw_printer": arr.bw_printer.id if arr.bw_printer else None,
        }
        for arr in arrangements
    ]
