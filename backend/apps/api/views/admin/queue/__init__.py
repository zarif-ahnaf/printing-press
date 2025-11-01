from ninja import Query, Router

from apps.queue.models import Queue

from ....auth import AuthBearer
from ....decorators import admin_required
from ....filters.queue import QueueFilter
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
def list_queue(
    request: HttpRequest,
    query: Query[QueueFilter],
):
    queryset = Queue.objects.all()

    if not query.include_processed:
        queryset = Queue.objects.filter(processed=False)

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
