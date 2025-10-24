from http import HTTPStatus

from django.http import HttpResponse
from ninja import Router

from ...auth import AuthBearer
from ...http import HttpRequest
from ...models import Token

router = Router(tags=["User"])


@router.delete("", auth=AuthBearer())
def post_user_logout_info(request: HttpRequest) -> HttpResponse:
    token: Token = Token.objects.get(user=request.auth)
    token.delete()
    return HttpResponse("Successful", status=HTTPStatus.ACCEPTED)
