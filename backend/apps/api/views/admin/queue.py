from ninja import Router, File, Form
from ninja.files import UploadedFile
from ...auth import AuthBearer
from apps.queue.models import Queue
from ...decorators import admin_required
from django.contrib.auth.models import User
from ninja.errors import HttpError
from django.db import transaction

router = Router(tags=["Queue"])


@router.post(
    "",
    auth=AuthBearer(),
)
@admin_required
def queue_files(
    request,
    user_id: Form[int],
    files: File[list[UploadedFile]],
):
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found.")

    if not files:
        return {"message": "No files provided"}

    with transaction.atomic():
        queue_objects = []
        for file in files:
            queue_obj = Queue(file=file, user=target_user)
            queue_objects.append(queue_obj)

        Queue.objects.bulk_create(queue_objects)

    return {"message": f"{len(files)} file(s) queued successfully"}
