from ninja import Router
from ninja.errors import HttpError
from decimal import Decimal
from django.db import transaction as db_transaction
from django.contrib.auth.models import User
from apps.wallet.models import Wallet, Transaction
from ...auth import AuthBearer
from ...http import HttpRequest
from ...decorators import admin_required
from ...schemas.admin import AdminChargePayload, AdminChargeResponse

router = Router(tags=["Admin Wallet"])


@router.post(
    "",
    auth=AuthBearer(),
    response={
        200: AdminChargeResponse,
        400: dict,
        403: dict,  # Forbidden
        404: dict,  # User not found
    },
)
@admin_required
def admin_charge_wallet(request: HttpRequest, payload: AdminChargePayload):
    # Validate amount
    if payload.amount <= 0:
        raise HttpError(400, "Amount must be greater than zero.")

    try:
        amount_decimal = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    except Exception as e:
        raise HttpError(400, f"Invalid amount: {str(e)}")

    # Fetch target user
    try:
        target_user = User.objects.get(id=payload.user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found.")

    # Perform charge in atomic transaction
    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get_or_create(user=target_user)[0]

        # Deduct amount
        wallet.balance -= amount_decimal
        wallet.save()

        # Log transaction
        Transaction.objects.create(
            wallet=wallet,
            user=target_user,
            transaction_type="charge",
            amount=amount_decimal,
            description=payload.description or "Admin charge",
        )

    return AdminChargeResponse(
        message="Admin charge successful.",
        charged_amount=float(amount_decimal),
        remaining_balance=float(wallet.balance),
        user_id=target_user.pk,
    )
