from django.http import HttpRequest as DjangoHttpRequest
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import User


class HttpRequest(DjangoHttpRequest):
    auth: User | AnonymousUser


__all__ = ["HttpRequest"]
