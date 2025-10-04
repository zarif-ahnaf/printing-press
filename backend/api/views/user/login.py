from ...models import Token
from django.contrib.auth import authenticate
from django.http import Http404, HttpRequest
from ninja import Form, Router
from ...schemas.login import LoginSchema


router = Router(tags=["User"])


@router.post("/login", response=LoginSchema)
def post_user_login_info(
    request: HttpRequest,
    username: Form[str],
    password: Form[str],
) -> Token:
    user = authenticate(request, username=username, password=password)

    if user is None:
        raise Http404("No such user exists or invalid credentials")

    if not user.is_active:
        raise Http404("User account is disabled")

    token, _ = Token.objects.get_or_create(user=user)
    return token
