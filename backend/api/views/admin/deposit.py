from ninja import Router
from ninja.errors import HttpError
from django.db import transaction as db_transaction
from django.contrib.auth.models import User
from decimal import Decimal, InvalidOperation

from wallet.models import Wallet, Transaction
from ...auth import AuthBearer
from ...http import HttpRequest
from ...decorators import admin_required
from ...schemas.admin import AdminDepositPayload

router = Router(tags=["Admin Wallet"])


@router.post(
    "",
    auth=AuthBearer(),
    response={
        200: dict,
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
    try:
        target_user = User.objects.get(id=payload.user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found.")

    try:
        amount = Decimal(payload.amount)
    except InvalidOperation:
        raise HttpError(400, "Invalid amount format. Must be a valid decimal string.")

    if amount <= 0:
        raise HttpError(400, "Amount must be greater than zero.")

    wallet, _ = Wallet.objects.get_or_create(user=target_user)

    # Use provided description or generate default
    if payload.description is not None:
        description = payload.description
    else:
        description = f"Admin deposit by {request.auth.username}"

    with db_transaction.atomic():
        wallet.deposit(amount)
        Transaction.objects.create(
            wallet=wallet,
            user=target_user,
            transaction_type="deposit",
            amount=amount,
            description=description,
        )

    return {
        "success": True,
        "user_id": target_user.pk,
        "username": target_user.username,
        "amount_deposited": str(amount),
        "new_balance": str(wallet.balance),
        "message": f"Successfully deposited {amount} to user {target_user.username}'s wallet.",
    }
