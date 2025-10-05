# your_app/api.py
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from wallet.models import Wallet
from ..auth import AuthBearer

router = Router()


class BalanceResponse(Schema):
    balance: str


@router.get("", auth=AuthBearer(), response=BalanceResponse)
def get_balance(request):
    """
    Returns the authenticated user's wallet balance.
    """
    user = request.auth
    wallet = get_object_or_404(Wallet, user=user)
    return {"balance": str(wallet.balance)}
