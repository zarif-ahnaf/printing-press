from django.contrib.auth.models import User
from ninja import Router

from apps.wallet.models import Transaction

from ....auth import AuthBearer
from ....decorators import admin_required
from ....http import HttpRequest
from ....schemas.transaction import TransactionResponse

router = Router(tags=["Transactions"])


@router.get(
    "/{username}",
    auth=AuthBearer(),
    response=list[TransactionResponse],
)
@admin_required
def list_user_transactions(
    request: HttpRequest,
    username: str,
):
    target_user = User.objects.get(username=username)

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
