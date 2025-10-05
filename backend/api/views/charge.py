from ninja import Router
from ninja.errors import HttpError
from decimal import Decimal
from django.db import transaction as db_transaction
from ..auth import AuthBearer
from ..http import HttpRequest
from wallet.models import Wallet, Transaction
from ..schemas.wallet import ChargeRequest, ChargeResponse

router = Router(tags=["Wallet"])


@router.post(
    "/charge",
    auth=AuthBearer(),
    response={
        200: ChargeResponse,
        400: dict,
    },
)
def charge_wallet(request: HttpRequest, payload: ChargeRequest):
    user = request.auth

    if payload.amount <= 0:
        raise HttpError(400, "Amount must be greater than zero.")

    try:
        amount_decimal = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    except Exception as e:
        raise HttpError(400, f"Invalid amount format: {str(e)}")

    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)

        # Deduct amount
        wallet.balance -= amount_decimal
        wallet.save()

        # Record transaction
        Transaction.objects.create(
            wallet=wallet,
            user=user,
            transaction_type="charge",
            amount=amount_decimal,
            description=payload.description or "Manual charge",
        )

    return ChargeResponse(
        message="Amount successfully charged.",
        charged_amount=float(amount_decimal),
        remaining_balance=float(wallet.balance),
    )
