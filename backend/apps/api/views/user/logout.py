from ...models import Token
from django.http import HttpResponse
from ninja import Router
from http import HTTPStatus
from ...auth import AuthBearer
from ...http import HttpRequest

router = Router(tags=["User"])


@router.delete("", auth=AuthBearer())
def post_user_logout_info(request: HttpRequest) -> HttpResponse:
    token: Token = Token.objects.get(user=request.auth)
    token.delete()
    return HttpResponse("Successful", status=HTTPStatus.ACCEPTED)
