from ninja import Router, File
from ninja.files import UploadedFile
from ..auth import AuthBearer
from apps.queue.models import Queue

router = Router(tags=["Queue"])


@router.post(
    "",
    auth=AuthBearer(),
)
def queue_files(
    request,
    file: File[UploadedFile],
):
    queue_item = Queue.objects.create(file=file, user=request.auth)

    return {"message": "File queued successfully", "queue_id": queue_item.pk}
