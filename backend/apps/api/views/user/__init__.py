from ninja import Router
from ...http import HttpRequest
from ...auth import AuthBearer
from ...schemas.user import UserSchema

router = Router()


@router.get("", auth=AuthBearer(), response=UserSchema)
def get_current_user_info(request: HttpRequest):
    user = request.auth
    return user
