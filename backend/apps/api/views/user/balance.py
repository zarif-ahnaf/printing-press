from django.shortcuts import get_object_or_404
from ninja import Router

from apps.wallet.models import Wallet

from ...auth import AuthBearer
from ...http import HttpRequest
from ...schemas.balance import BalanceResponse

router = Router(tags=["User"])


@router.get("", auth=AuthBearer(), response=BalanceResponse)
def get_balance(request: HttpRequest):
    """
    Returns the authenticated user's wallet balance.
    """
    user = request.auth
    wallet = get_object_or_404(Wallet, user=user)
    return BalanceResponse(balance=str(wallet.balance))
