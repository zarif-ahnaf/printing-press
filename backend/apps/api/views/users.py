from django.contrib.auth.models import User
from django.db.models import Q
from ninja import Query, Router

from ..filters.user import UserFilter
from ..http import HttpRequest
from ..schemas.user import UserSchema

router = Router(tags=["User"])


@router.get("", response=list[UserSchema])
def show_all_users(
    request: HttpRequest,
    query: Query[UserFilter],
):
    queryset = User.objects.all()

    if name := query.name:
        queryset = queryset.filter(
            Q(first_name__icontains=name)
            | Q(last_name__icontains=name)
            | Q(username__icontains=name)
        )

    return [
        UserSchema(
            id=user.pk,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_staff=user.is_staff,
            is_superuser=user.is_superuser,
            date_joined=user.date_joined,
        )
        for user in queryset
    ]
