from ninja import Router

from apps.printers.models import Printers

from ...schemas.printer import PrinterOutSchema

router = Router(tags=["Printers"])


@router.get("", response=list[PrinterOutSchema])
def printer_list(request):
    data = Printers.objects.all()
    return data
