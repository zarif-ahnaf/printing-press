from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, UploadedFile

from apps.printers.models import Printers

from ....auth import AuthBearer
from ....decorators import admin_required
from ....http import HttpRequest
from ....schemas.printer import (
    PrinterDecomissionSchema,
    PrinterOutSchema,
    PrinterUpdateSchema,
)

router = Router(tags=["Admin Printers"])


@router.patch("{printer_id}", auth=AuthBearer(), response=PrinterOutSchema)
@admin_required
def printers_update(
    request: HttpRequest,
    printer_id: int,
    payload: Form[PrinterUpdateSchema],
    image: File[UploadedFile] = None,  # type: ignore
):
    printer = get_object_or_404(Printers, id=printer_id)
    printer.name = payload.name
    printer.is_color = payload.is_color
    printer.simplex_charge = payload.simplex_charge
    printer.duplex_charge = payload.duplex_charge
    printer.decomissioned = payload.decomissioned
    if image:
        printer.image = image
    printer.save()
    return PrinterOutSchema(
        name=printer.name,
        is_color=printer.is_color,
        id=printer.pk,
        simplex_charge=printer.simplex_charge,
        duplex_charge=printer.duplex_charge,
        decomissioned=printer.decomissioned,
        image=request.build_absolute_uri(printer.image.url),
    )


@router.delete(
    "{printer_id}/decomission", auth=AuthBearer(), response=PrinterDecomissionSchema
)
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


@router.post(
    "{printer_id}/decomission", auth=AuthBearer(), response=PrinterDecomissionSchema
)
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
