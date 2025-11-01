from functools import wraps

from django.contrib.auth.models import AnonymousUser
from ninja.errors import HttpError

from .http import HttpRequest


def admin_required(view_func):
    """
    Decorator to restrict a Ninja view to admin or superuser only.

    Assumes:
      - The request is authenticated (e.g., via AuthBearer)
      - request.auth is a Django User instance
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not hasattr(request, "auth"):
            raise ValueError(
                "Decorator object has no 'auth' attribute. Ensure authentication is set up correctly."
            )

        user = request.auth

        if not hasattr(user, "is_staff") or isinstance(user, AnonymousUser):
            raise HttpError(401, "Authentication required.")

        if not (user.is_staff or user.is_superuser):
            raise HttpError(403, "Admin access required.")

        return view_func(request, *args, **kwargs)

    return wrapper


def login_required(view_func):
    """
    Decorator to restrict a Ninja view to authenticated users only.

    Assumes:
      - The request is authenticated (e.g., via AuthBearer)
      - request.auth is a Django User instance
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        user = request.auth

        if not hasattr(user, "is_authenticated") or isinstance(user, AnonymousUser):
            raise HttpError(401, "Authentication required.")

        if not user.is_authenticated:
            raise HttpError(401, "Authentication required.")

        return view_func(request, *args, **kwargs)

    return wrapper
