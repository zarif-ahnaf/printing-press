from ninja import Schema


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
    user_id: int
    amount: str
    description: str | None = None
