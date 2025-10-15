from ninja import Router
from ninja.errors import HttpError
from decimal import Decimal, InvalidOperation
from django.db import transaction as db_transaction
from django.contrib.auth.models import User
from apps.wallet.models import Wallet, Transaction
from ..auth import AuthBearer
from ..http import HttpRequest
from ..schemas.wallet import ChargeRequest, ChargeResponse

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
    requester = request.auth  # This is the authenticated user

    # Validate amount
    if payload.amount <= 0:
        raise HttpError(400, "Amount must be greater than zero.")

    try:
        amount_decimal = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise HttpError(400, f"Invalid amount format: {str(e)}")

    # Determine target user
    if payload.user_id is not None:
        # Admin mode: must be admin to charge another user
        if not (hasattr(requester, "is_staff") and requester.is_staff):
            raise HttpError(403, "Only admins can charge other users' wallets.")

        try:
            target_user = User.objects.get(id=payload.user_id)
        except User.DoesNotExist:
            raise HttpError(404, "Target user not found.")
    else:
        # Regular mode: charge own wallet
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
