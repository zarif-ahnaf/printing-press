from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from decimal import Decimal, InvalidOperation
from django.db import transaction as db_transaction
from django.contrib.auth.models import User
from apps.wallet.models import Wallet, Transaction
from ..auth import AuthBearer
from ..http import HttpRequest
from ..schemas.wallet import ChargeRequest, ChargeResponse
from ..decorators import admin_required

router = Router(tags=["Wallet"])


@router.post(
    "",
    auth=AuthBearer(),
    response={
        200: ChargeResponse,
        400: dict,
        403: dict,
        404: dict,
    },
)
def charge_wallet(request: HttpRequest, payload: ChargeRequest):
    requester = request.auth

    # Validate amount
    if payload.amount <= 0:
        raise HttpError(400, "Amount must be greater than zero.")

    try:
        amount_decimal = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise HttpError(400, f"Invalid amount format: {str(e)}")

    # Determine target user
    if payload.user_id is not None:
        if not (hasattr(requester, "is_staff") and requester.is_staff):
            raise HttpError(403, "Only admins can charge other users' wallets.")
        target_user = get_object_or_404(User, id=payload.user_id)
    else:
        target_user = requester

    # Perform atomic charge
    with db_transaction.atomic():
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=target_user)
        wallet.balance -= amount_decimal
        wallet.save(update_fields=["balance"])

        Transaction.objects.create(
            wallet=wallet,
            user=target_user,
            transaction_type="charge",
            amount=amount_decimal,
            description=payload.description
            or ("Admin charge" if payload.user_id else "Manual charge"),
        )

    return ChargeResponse(
        message="Wallet charged successfully.",
        charged_amount=float(amount_decimal),
        remaining_balance=float(wallet.balance),
    )


@router.post(
    "/{username}",
    auth=AuthBearer(),
    response={
        200: ChargeResponse,
        400: dict,
        403: dict,
        404: dict,
    },
)
@admin_required
def charge_wallet_for_user(request: HttpRequest, username: str, payload: ChargeRequest):
    if payload.amount <= 0:
        raise HttpError(400, "Amount must be greater than zero.")

    try:
        amount_decimal = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise HttpError(400, f"Invalid amount format: {str(e)}")

    # Fetch target user by username (404 if not found)
    target_user = get_object_or_404(User, username=username)

    # Perform atomic charge
    with db_transaction.atomic():
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=target_user)
        wallet.balance -= amount_decimal
        wallet.save(update_fields=["balance"])

        Transaction.objects.create(
            wallet=wallet,
            user=target_user,
            transaction_type="charge",
            amount=amount_decimal,
            description=payload.description or "Admin charge (by username)",
        )

    return ChargeResponse(
        message="Wallet charged successfully.",
        charged_amount=float(amount_decimal),
        remaining_balance=float(wallet.balance),
    )
