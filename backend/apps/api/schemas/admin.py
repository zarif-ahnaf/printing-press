from ninja import Schema
from decimal import Decimal
from pydantic import ConfigDict


class AdminChargePayload(Schema):
    user_id: int
    amount: float
    description: str = "Admin-initiated charge"


class AdminChargeResponse(Schema):
    message: str
    charged_amount: float
    remaining_balance: float
    user_id: int


class AdminDepositPayload(Schema):
    username: str
    amount: str
    description: str | None = None


class AdminDepositResponse(Schema):
    success: bool
    user_id: int
    username: str
    amount_deposited: Decimal
    new_balance: Decimal
    message: str

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: str(v),
        }
    )
