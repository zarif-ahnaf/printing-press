from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, UploadedFile

from apps.printers.models import Printers

from ....decorators import admin_required
from ....http import HttpRequest
from ....schemas.printer import (
    PrinterCreateSchema,
    PrinterDecomissionSchema,
    PrinterOutSchema,
)

router = Router(tags=["Admin Printers"])


@router.patch("{printer_id}/", response=PrinterOutSchema)
@admin_required
def printers_update(
    request: HttpRequest,
    printer_id: int,
    image: File[UploadedFile] | None = None,
    payload: Form[PrinterCreateSchema] | None = None,
):
    printer = get_object_or_404(Printers, id=printer_id)

    if payload:
        printer.name = payload.name
        printer.is_color = payload.is_color
        printer.simplex_charge = payload.simplex_charge
        printer.duplex_charge = payload.duplex_charge

    if image:
        printer.image = image

    printer.save()
    return printer


@router.delete("{printer_id}/decomission", response=PrinterDecomissionSchema)
@admin_required
def printers_decomission(
    request: HttpRequest,
    printer_id: int,
):
    printer = get_object_or_404(Printers, id=printer_id)
    printer.decomissioned = True
    printer.save()
    return PrinterDecomissionSchema(
        id=printer.pk,
        decomissioned=printer.decomissioned,
        message=f"Printer {printer.name} has been decomissioned.",
    )


@router.post("{printer_id}/decomission", response=PrinterDecomissionSchema)
@admin_required
def printers_recommission(
    request: HttpRequest,
    printer_id: int,
):
    printer = get_object_or_404(Printers, id=printer_id)
    printer.decomissioned = False
    printer.save()
    return PrinterDecomissionSchema(
        id=printer.pk,
        decomissioned=printer.decomissioned,
        message=f"Printer {printer.name} has been recommissioned.",
    )
