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

router = Router(tags=["Queue"])

COST_PER_PAGE = Decimal("1.0")


@router.post("", auth=AuthBearer())
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
        return {"message": "No files provided"}

    # Validate all files first (PDF + page count)
    total_pages = 0
    file_data_list: list[tuple[str, bytes, int]] = []  # (filename, content, page_count)

    for uploaded_file in files:
        filename = uploaded_file.name
        if not filename:
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

        total_pages += num_pages
        file_data_list.append((filename, file_content, num_pages))

    if total_pages == 0:
        return {"error": "No valid pages found in uploaded files"}, 400

    # Decide whether to charge
    is_admin_upload = user_id is not None  # i.e., admin acting on behalf of someone

    with transaction.atomic():
        queue_items = []
        transaction_records = []

        if not is_admin_upload:
            # Non-admin: charge the current user (who is also target_user)
            wallet = Wallet.objects.select_for_update().get_or_create(user=target_user)[
                0
            ]
            total_cost = COST_PER_PAGE * total_pages

            # Pre-check: can they afford it?
            if wallet.balance < total_cost:
                return {"error": "Insufficient wallet balance"}, 400

            # Now charge per file (as in original logic)
            for filename, content, num_pages in file_data_list:
                file_cost = COST_PER_PAGE * num_pages
                try:
                    wallet.charge(
                        file_cost,
                        description=f"Queue {filename} - {num_pages} page(s) - {file_cost} BDT",
                    )
                except ValueError as e:
                    return {"error": str(e)}, 400

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

        else:
            # Admin upload: no charging, just queue for target_user
            for filename, content, num_pages in file_data_list:
                file_for_db = SimpleUploadedFile(
                    name=filename, content=content, content_type="application/pdf"
                )
                queue_items.append(Queue(file=file_for_db, user=target_user))

        # Create queue items in all cases
        created_items = Queue.objects.bulk_create(queue_items)

    response = {
        "message": f"{len(created_items)} file(s) queued successfully",
        "total_pages": total_pages,
        "queue_ids": [item.pk for item in created_items],
    }

    if not is_admin_upload:
        response["total_charged_bdt"] = str(COST_PER_PAGE * total_pages)

    return response
