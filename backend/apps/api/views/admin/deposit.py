from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from apps.wallet.models import Transaction, Wallet

from ...auth import AuthBearer
from ...decorators import admin_required
from ...http import HttpRequest
from ...schemas.admin import AdminDepositPayload, AdminDepositResponse

router = Router(tags=["Admin Wallet"])


@router.post(
    "",
    auth=AuthBearer(),
    response={
        200: AdminDepositResponse,
        400: dict,
        403: dict,
        404: dict,
    },
)
@admin_required
def admin_deposit(
    request: HttpRequest,
    payload: AdminDepositPayload,
):
    target_user = get_object_or_404(User, username=payload.username)

    try:
        amount = Decimal(payload.amount)
    except InvalidOperation:
        raise HttpError(400, "Invalid amount format. Must be a valid decimal string.")

    if amount <= 0:
        raise HttpError(400, "Amount must be greater than zero.")

    wallet, _ = Wallet.objects.get_or_create(user=target_user)

    description = payload.description or f"Admin deposit by {request.auth.username}"

    with db_transaction.atomic():
        wallet.deposit(amount)
        Transaction.objects.create(
            wallet=wallet,
            user=target_user,
            transaction_type="deposit",
            amount=amount,
            description=description,
        )

    return AdminDepositResponse(
        success=True,
        user_id=target_user.pk,
        username=target_user.username,
        amount_deposited=amount,
        new_balance=wallet.balance,
        message=f"Successfully deposited {amount} to user {target_user.username}'s wallet.",
    )
