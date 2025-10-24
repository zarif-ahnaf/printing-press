# your_app/api.py
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from apps.wallet.models import Wallet

from ...auth import AuthBearer
from ...decorators import admin_required

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


@router.get("/{username}", auth=AuthBearer(), response=BalanceResponse)
@admin_required
def get_user_balance(request, username: str):
    """
    Returns the authenticated user's wallet balance.
    """
    target_user = get_object_or_404(User, username=username)

    wallet = get_object_or_404(Wallet, user=target_user)
    return {"balance": str(wallet.balance)}
