from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.queue.models import Queue

from ...auth import AuthBearer
from ...decorators import login_required
from ...http import HttpRequest
from ...schemas.queue import QueueFileResponse, QueueListResponse

router = Router(tags=["Queue"])


@router.get("", auth=AuthBearer(), response=QueueListResponse)
@login_required
def list_queue_by_user(
    request: HttpRequest,
):
    target_user = get_object_or_404(User, id=request.auth.pk)
    queryset = Queue.objects.filter(user=target_user)

    items = [
        QueueFileResponse(
            id=item.pk,
            file=request.build_absolute_uri(item.file.url),
            processed=item.processed,
            created_at=item.created_at.isoformat(),
            user=item.user.username,
            user_id=item.user.pk,
            page_count=item.page_count,
            print_mode=item.print_mode,
        )
        for item in queryset
    ]

    return QueueListResponse(queue=items)
