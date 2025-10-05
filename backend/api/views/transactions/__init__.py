from ninja import Router
from django.contrib.auth.models import User
from typing import List

from wallet.models import Transaction
from ...http import HttpRequest
from ...schemas.transaction import TransactionResponse
from ...auth import AuthBearer

router = Router(tags=["Transactions"])


@router.get(
    "",
    auth=AuthBearer(),
    response={
        200: List[TransactionResponse],
        403: dict,
        404: dict,
        400: dict,
    },
)
def admin_list_user_transactions(
    request: HttpRequest,
):
    target_user = User.objects.get(pk=request.auth.pk)

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
