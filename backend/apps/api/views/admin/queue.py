from ninja import Router, File, Form
from ninja.files import UploadedFile
from ...auth import AuthBearer
from apps.queue.models import Queue
from ...decorators import admin_required
from django.contrib.auth.models import User
from ninja.errors import HttpError

router = Router(tags=["Queue"])


@router.post(
    "",
    auth=AuthBearer(),
)
@admin_required
def queue_files(
    request,
    user_id: Form[int],
    file: File[UploadedFile],
):
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found.")

    queue_item = Queue.objects.create(file=file, user=target_user)

    return {"message": "File queued successfully", "queue_id": queue_item.pk}
