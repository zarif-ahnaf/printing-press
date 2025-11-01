from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.wallet.models import Transaction

from ...auth import AuthBearer
from ...decorators import login_required
from ...http import HttpRequest
from ...schemas.transaction import TransactionResponse

router = Router(tags=["User"])


@router.get(
    "",
    auth=AuthBearer(),
    response={
        200: list[TransactionResponse],
        403: dict,
        404: dict,
        400: dict,
    },
)
@login_required
def get_user_transactions_by_username(
    request: HttpRequest,
):
    """
    Get transaction history for a specific user by username.
    """
    # Get the target user by username
    target_user = get_object_or_404(User, username=request.auth.username)

    # Get transactions for the target user
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
