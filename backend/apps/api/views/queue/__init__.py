from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.queue.models import Queue

from ...auth import AuthBearer
from ...http import HttpRequest
from ...schemas.queue import (
    ChangePrintModeRequest,
    ChangeProcessStatusResponse,
    ProcessStatusResponse,
    QueueDeleteResponse,
    QueueFileUpload,
    QueueUploadResponse,
)
from ...utils.pdf import count_pdf_pages

router = Router(tags=["Queue"])

COST_PER_PAGE = Decimal("1.0")


@router.post(
    "",
    auth=AuthBearer(),
    response=QueueUploadResponse,
    summary="Queue files for processing",
)
def queue_files(
    request: HttpRequest,
    files: File[list[UploadedFile]],
    payload: Form[QueueFileUpload],
):
    current_user = request.auth

    # Determine target user
    if payload.user_id is not None:
        if not current_user.is_staff:
            raise HttpError(403, "Only admins can specify a user_id.")
        try:
            target_user = User.objects.get(id=payload.user_id)
        except User.DoesNotExist:
            raise HttpError(404, "User not found.")
    else:
        target_user = current_user

    if not files:
        raise HttpError(400, "No files provided")

    total_pages = 0
    file_data_list: list[tuple[str, bytes, int]] = []

    for uploaded_file in files:
        filename = uploaded_file.name
        if not filename:
            raise HttpError(400, "Uploaded file has no name")
        if not filename.lower().endswith(".pdf"):
            raise HttpError(400, f"Only PDF files allowed. Invalid: {filename}")

        file_content = uploaded_file.read()
        if not file_content:
            raise HttpError(400, f"File {filename} is empty.")

        try:
            num_pages = count_pdf_pages(file_content, filename)
        except ValueError as e:
            raise HttpError(400, str(e))

        if num_pages <= 0:
            raise HttpError(400, f"No valid pages found in {filename}")

        total_pages += num_pages
        file_data_list.append((filename, file_content, num_pages))

    if total_pages == 0:
        raise HttpError(400, "No valid pages found in uploaded files")

    # Create Queue objects with page_count
    queue_items = []
    for filename, content, num_pages in file_data_list:
        file_for_db = SimpleUploadedFile(
            name=filename,
            content=content,
            content_type="application/pdf",
        )
        queue_items.append(
            Queue(
                file=file_for_db,
                user=target_user,
                page_count=num_pages,
            )
        )

    created_items = Queue.objects.bulk_create(queue_items)

    return QueueUploadResponse(
        message=f"{len(created_items)} file(s) queued successfully",
        total_pages=total_pages,
        queue_ids=[item.pk for item in created_items],
        total_charged_bdt=str(COST_PER_PAGE * total_pages),
    )


@router.post("{queue_id}/print-mode", auth=AuthBearer())
def change_page_mode(
    request: HttpRequest, payload: ChangePrintModeRequest, queue_id: int
):
    queue_item = get_object_or_404(Queue, id=queue_id)
    current_user = request.auth
    if queue_item.user != current_user and not current_user.is_staff:
        raise HttpError(403, "You cannot modify this queue item.")
    old_mode = queue_item.print_mode
    queue_item.print_mode = payload.page_type
    queue_item.save()
    return ChangeProcessStatusResponse(
        id=queue_item.pk,
        message=f"Print mode updated from {old_mode} to {queue_item.print_mode}",
    )


@router.delete(
    "{queue_id}/delete",
    auth=AuthBearer(),
    response=QueueDeleteResponse,
    summary="Mark file as unprocessed",
)
def remove_queue_file(
    request: HttpRequest,
    queue_id: int,
):
    current_user = request.auth
    queue_item = get_object_or_404(Queue, id=queue_id)

    if queue_item.user != current_user and not current_user.is_staff:
        raise HttpError(403, "You cannot modify this queue item.")

    deleted_id = queue_item.pk

    queue_item.delete()

    return QueueDeleteResponse(
        id=deleted_id,
        message=f"{queue_item.pk} has been deleted successfully.",
    )


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
    return ProcessStatusResponse(
        id=queue_item.pk,
        processed=queue_item.processed,
        message="File marked as processed.",
    )


@router.delete(
    "/{queue_id}/processed",
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

    return ProcessStatusResponse(
        id=queue_item.pk,
        processed=queue_item.processed,
        message="File marked as unprocessed.",
    )
