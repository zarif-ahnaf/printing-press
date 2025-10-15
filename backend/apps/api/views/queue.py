from typing import List, Tuple
from ninja import Router, File
from ninja.files import UploadedFile
from ..auth import AuthBearer
from apps.queue.models import Queue
from django.db import transaction
from ..http import HttpRequest
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile

from ..utils.pdf import count_pdf_pages

from apps.wallet.models import Wallet, Transaction

router = Router(tags=["Queue"])

COST_PER_PAGE = Decimal("1.0")


@router.post("", auth=AuthBearer())
def queue_files(
    request: HttpRequest,
    files: File[List[UploadedFile]],
):
    if not files:
        return {"message": "No files provided"}

    user = request.auth
    total_pages = 0
    file_data_list: List[
        Tuple[str, bytes, int, Decimal]
    ] = []  # (filename, content, page_count, cost)

    # Step 1: Validate, count pages, and compute per-file cost
    for uploaded_file in files:
        filename = uploaded_file.name
        if filename is None:
            return {"error": "Uploaded file has no name"}, 400

        if not filename.lower().endswith(".pdf"):
            return {"error": f"Only PDF files allowed. Invalid: {filename}"}, 400

        file_content = uploaded_file.read()
        try:
            num_pages = count_pdf_pages(file_content, filename)
        except ValueError as e:
            return {"error": str(e)}, 400

        if num_pages == 0:
            return {"error": f"No valid pages found in {filename}"}, 400

        file_cost = COST_PER_PAGE * num_pages
        total_pages += num_pages
        file_data_list.append((filename, file_content, num_pages, file_cost))

    if total_pages == 0:
        return {"error": "No valid pages found in uploaded files"}, 400

    total_cost = COST_PER_PAGE * total_pages

    # Step 2: Atomic transaction — validate balance, charge per file, create per-file transactions & queue items
    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get_or_create(user=user)[0]

        queue_items = []
        transaction_records = []

        for filename, content, num_pages, file_cost in file_data_list:
            # Deduct this file's cost
            try:
                wallet.charge(
                    file_cost,
                    description=f"Queue {filename} - {num_pages} page(s) - {file_cost} BDT",
                )
            except ValueError as e:
                return {"error": str(e)}, 400

            # Create a transaction record for this file
            transaction_records.append(
                Transaction(
                    wallet=wallet,
                    user=user,
                    transaction_type="charge",
                    amount=file_cost,
                    description=f"{filename} - page {num_pages} - price {file_cost}",
                )
            )

            # Prepare queue item
            file_for_db = SimpleUploadedFile(
                name=filename, content=content, content_type="application/pdf"
            )
            queue_items.append(Queue(file=file_for_db, user=user))

        # Bulk create all at once
        Transaction.objects.bulk_create(transaction_records)
        created_items = Queue.objects.bulk_create(queue_items)

    return {
        "message": f"{len(created_items)} file(s) queued successfully",
        "total_pages": total_pages,
        "total_charged_bdt": str(total_cost),
        "queue_ids": [item.pk for item in created_items],
    }
