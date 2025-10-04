from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth import get_user_model
from typing import List

from wallet.models import Transaction
from ...http import HttpRequest
from ...schemas.transaction import TransactionResponse

User = get_user_model()
router = Router(tags=["Transactions"])


@router.get(
    "",
    response={
        200: List[TransactionResponse],
        403: dict,
        404: dict,
        400: dict,
    },
)
def admin_list_user_transactions(
    request: HttpRequest,
    user_id: int,
):
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found.")

    transactions = Transaction.objects.filter(user=target_user).order_by("-created_at")

    return [
        TransactionResponse(
            id=txn.pk,
            transaction_type=txn.transaction_type,
            amount=str(txn.amount),
            description=txn.description,
            created_at=txn.created_at.isoformat(),
        )
        for txn in transactions
    ]
