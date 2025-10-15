from ninja import Router, Query
from ..http import HttpRequest
from django.contrib.auth.models import User
from django.db.models import Q

router = Router(tags=["User"])


@router.get("")
def show_all_users(request: HttpRequest, name: Query[str] | None = None) -> list[dict]:
    queryset = User.objects.all()

    if name:
        queryset = User.objects.filter(
            Q(first_name__icontains=name) | Q(last_name__icontains=name)
        )

    return [
        {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        for user in queryset
    ]
