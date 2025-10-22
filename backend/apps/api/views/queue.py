from ninja import Router, File, Form
from ninja.files import UploadedFile
from ninja.errors import HttpError
from ..auth import AuthBearer
from apps.queue.models import Queue
from apps.wallet.models import Wallet, Transaction
from django.db import transaction
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from ..utils.pdf import count_pdf_pages
from ..http import HttpRequest
from django.shortcuts import get_object_or_404
from ..schemas.queue import (
    QueueUploadResponse,
    QueueListResponse,
    ProcessStatusResponse,
)

router = Router(tags=["Queue"])

COST_PER_PAGE = Decimal("1.0")


@router.post("", auth=AuthBearer(), response=QueueUploadResponse)
def queue_files(
    request: HttpRequest,
    files: File[list[UploadedFile]],
    user_id: Form[int] | None = None,
):
    current_user = request.auth
    # Determine target user
    if user_id is not None:
        # Admin trying to specify a user
        if not current_user.is_staff:
            raise HttpError(403, "Only admins can specify a user_id.")
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise HttpError(404, "User not found.")
    else:
        # Regular user uploading for themselves
        target_user = current_user

    if not files:
        # Note: This returns 200 with a message — acceptable if intentional
        return {"message": "No files provided"}

    total_pages = 0
    file_data_list: list[tuple[str, bytes, int]] = []  # (filename, content, page_count)

    for uploaded_file in files:
        filename = uploaded_file.name
        if not filename:
            raise HttpError(400, "Uploaded file has no name")

        if not filename.lower().endswith(".pdf"):
            raise HttpError(400, f"Only PDF files allowed. Invalid: {filename}")

        file_content = uploaded_file.read()
        try:
            num_pages = count_pdf_pages(file_content, filename)
        except ValueError as e:
            raise HttpError(400, str(e))

        if num_pages == 0:
            raise HttpError(400, f"No valid pages found in {filename}")

        total_pages += num_pages
        file_data_list.append((filename, file_content, num_pages))

    if total_pages == 0:
        raise HttpError(400, "No valid pages found in uploaded files")

    with transaction.atomic():
        queue_items = []
        transaction_records = []

        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=target_user, defaults={"balance": Decimal("0.00")}
        )
        # total_cost = COST_PER_PAGE * total_pages
        # # Pre-check: can they afford it?
        # if wallet.balance < total_cost:
        #     raise HttpError(400, "Insufficient wallet balance")

        # Now charge per file
        for filename, content, num_pages in file_data_list:
            file_cost = COST_PER_PAGE * num_pages
            try:
                wallet.charge(
                    file_cost,
                    description=f"Queue {filename} - {num_pages} page(s) - {file_cost} BDT",
                )
            except ValueError as e:
                raise HttpError(400, str(e))

            transaction_records.append(
                Transaction(
                    wallet=wallet,
                    user=target_user,
                    transaction_type="charge",
                    amount=file_cost,
                    description=f"Printed {filename} - {num_pages} pages - {file_cost} BDT",
                )
            )

            file_for_db = SimpleUploadedFile(
                name=filename, content=content, content_type="application/pdf"
            )
            queue_items.append(Queue(file=file_for_db, user=target_user))

        Transaction.objects.bulk_create(transaction_records)

        # Create queue items in all cases
        created_items = Queue.objects.bulk_create(queue_items)

    response = {
        "message": f"{len(created_items)} file(s) queued successfully",
        "total_pages": total_pages,
        "queue_ids": [item.pk for item in created_items],
        "total_charged_bdt": str(COST_PER_PAGE * total_pages),
    }

    return response


@router.get(
    "", auth=AuthBearer(), response=QueueListResponse, summary="List queued files"
)
def list_queue(
    request: HttpRequest,
):
    """
    Fetch all queued files for the current user.
    Admins can optionally see all users' queues
    """
    current_user = request.auth
    queryset = Queue.objects.filter(user=current_user)

    items = [
        {
            "id": item.pk,
            "file": request.build_absolute_uri(item.file.url),
            "processed": item.processed,
            "created_at": item.created_at.isoformat(),
            "user": item.user.username,
        }
        for item in queryset
    ]

    return {"queue": items}


@router.post(
    "/{queue_id}/processed",
    response=ProcessStatusResponse,
    auth=AuthBearer(),
    summary="Mark file as processed",
)
def mark_as_processed(
    request: HttpRequest,
    queue_id: int,
):
    current_user = request.auth
    queue_item = get_object_or_404(Queue, id=queue_id)

    if queue_item.user != current_user and not current_user.is_staff:
        raise HttpError(403, "You cannot modify this queue item.")

    queue_item.processed = True
    queue_item.save(update_fields=["processed", "updated_at"])

    return {
        "id": queue_item.pk,
        "processed": True,
        "message": "File marked as processed.",
    }


@router.delete(
    "/{queue_id}/processed",
    response=ProcessStatusResponse,
    auth=AuthBearer(),
    summary="Mark file as unprocessed",
)
def mark_as_unprocessed(
    request: HttpRequest,
    queue_id: int,
):
    current_user = request.auth
    queue_item = get_object_or_404(Queue, id=queue_id)

    if queue_item.user != current_user and not current_user.is_staff:
        raise HttpError(403, "You cannot modify this queue item.")

    queue_item.processed = False
    queue_item.save(update_fields=["processed", "updated_at"])

    return {
        "id": queue_item.pk,
        "processed": False,
        "message": "File marked as unprocessed.",
    }
