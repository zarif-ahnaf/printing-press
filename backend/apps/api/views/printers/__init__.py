from django.shortcuts import get_object_or_404
from ninja import Router

from apps.printers.models import Printers

from ...http import HttpRequest
from ...schemas.printer import PrinterOutSchema

router = Router(tags=["Printers"])


@router.get("", response=list[PrinterOutSchema])
def printer_list(request):
    printers = Printers.objects.all()
    data = [
        PrinterOutSchema(
            name=printer.name,
            id=printer.pk,
            is_color=printer.is_color,
            image=request.build_absolute_uri(printer.image.url),
            simplex_charge=printer.simplex_charge,
            duplex_charge=printer.duplex_charge,
            decomissioned=printer.decomissioned,
        )
        for printer in printers
    ]
    return data


@router.get("{printer_id}", response=PrinterOutSchema)
def printer_get(
    request: HttpRequest,
    printer_id: int,
):
    printer = get_object_or_404(Printers, id=printer_id)
    data = PrinterOutSchema(
        id=printer.pk,
        name=printer.name,
        image=request.build_absolute_uri(printer.image.url),
        is_color=printer.is_color,
        simplex_charge=printer.simplex_charge,
        duplex_charge=printer.duplex_charge,
        decomissioned=printer.decomissioned,
    )

    return data
