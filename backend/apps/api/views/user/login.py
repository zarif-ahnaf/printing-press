from ...models import Token
from django.contrib.auth import authenticate
from django.http import Http404, HttpRequest
from ninja import Form, Router
from ...schemas.login import LoginInSchema, LoginOutSchema


router = Router(tags=["User"])


@router.post("/login", response=LoginOutSchema)
def post_user_login_info(request: HttpRequest, payload: LoginInSchema) -> Token:
    user = authenticate(request, username=payload.username, password=payload.password)

    if user is None:
        raise Http404("No such user exists or invalid credentials")

    if not user.is_active:
        raise Http404("User account is disabled")

    token, _ = Token.objects.get_or_create(user=user)
    return token
