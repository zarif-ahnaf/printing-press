from ninja import Router, File
from ninja.files import UploadedFile
from ninja.errors import HttpError
from typing import List, Union
from django.db import transaction as db_transaction
from ..utils.pdf import process_pdf_file
from wallet.models import Wallet, Transaction
from ..auth import AuthBearer
from ..http import HttpRequest
from ..schemas.wallet import (
    UploadSuccessResponse,
    UploadNoChargeResponse,
    PDFUploadResult,
    PDFUploadError,
)

router = Router(tags=["PDF"])


@router.post(
    "",
    auth=AuthBearer(),
    response={
        200: Union[UploadSuccessResponse, UploadNoChargeResponse],
    },
)
def upload_pdfs(request: HttpRequest, files: File[List[UploadedFile]]):
    user = request.auth
    wallet, _ = Wallet.objects.get_or_create(user=user)

    results: List[Union[PDFUploadResult, PDFUploadError]] = []
    total_charge = 0
    processed_files = []

    for uploaded_file in files:
        filename = getattr(uploaded_file, "name", "") or ""
        if not filename.lower().endswith(".pdf"):
            results.append(
                PDFUploadError(
                    filename=filename or None, error="Only PDF files are allowed."
                )
            )
            continue

        try:
            summary, _ = process_pdf_file(uploaded_file=uploaded_file, return_pdf=False)
            charge = summary["non_blank_pages"]

            if charge < 0:
                raise ValueError("Invalid page count")

            results.append(
                PDFUploadResult(
                    filename=summary.get("filename", filename),
                    total_pages=summary["total_pages"],
                    non_blank_pages=summary["non_blank_pages"],
                    blank_pages=summary["blank_pages"],
                    charge_taka=charge,
                )
            )
            total_charge += charge
            processed_files.append((summary.get("filename", filename), charge))

        except Exception as e:
            results.append(PDFUploadError(filename=filename or None, error=str(e)))

    if total_charge == 0:
        return UploadNoChargeResponse(
            uploads=results,
            total_charge_taka=0,
            message="No valid PDFs to charge.",
        )

    try:
        with db_transaction.atomic():
            wallet.balance -= total_charge
            wallet.save()

            for filename, charge in processed_files:
                Transaction.objects.create(
                    wallet=wallet,
                    user=user,
                    transaction_type="charge",
                    amount=charge,
                    description=f"Printed '{filename}' ({charge} non-blank pages)",
                )

    except Exception as e:
        # For unexpected errors, raise 500
        raise HttpError(500, f"Payment processing failed: {str(e)}")

    return UploadSuccessResponse(
        uploads=results,
        total_files_processed=len(processed_files),
        total_charge_taka=total_charge,
        remaining_balance=float(wallet.balance),
        message=f"Successfully charged {total_charge} taka. Remaining balance: {wallet.balance} taka",
    )
