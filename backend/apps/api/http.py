from typing import NoReturn

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest as DjangoHttpRequest


class HttpRequest(DjangoHttpRequest):
    auth: User | AnonymousUser

    @property
    def user(self) -> NoReturn:  # type: ignore[override]
        raise AttributeError(
            "'HttpRequest' object has no attribute 'user'. "
            "Use 'request.auth' instead for authentication information."
        )


__all__ = ["HttpRequest"]
