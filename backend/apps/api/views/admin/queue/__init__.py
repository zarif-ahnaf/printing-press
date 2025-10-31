from ninja import Router

from apps.queue.models import Queue

from ....auth import AuthBearer
from ....decorators import admin_required
from ....http import HttpRequest
from ....schemas.queue import QueueFileResponse, QueueListResponse

router = Router(tags=["Queue"])


@router.get(
    "",
    auth=AuthBearer(),
    response=QueueListResponse,
    summary="List queued files",
)
@admin_required
def list_queue(request: HttpRequest):
    queryset = Queue.objects.all()

    items = [
        QueueFileResponse(
            id=item.pk,
            file=request.build_absolute_uri(item.file.url),
            processed=item.processed,
            created_at=item.created_at.isoformat(),
            print_mode=item.print_mode,
            user=item.user.username,
            user_id=item.user.pk,
            
            page_count=item.page_count,
        )
        for item in queryset
    ]

    return QueueListResponse(queue=items)
