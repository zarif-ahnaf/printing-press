from ninja import Schema


class ChargeRequest(Schema):
    amount: float
    description: str = "Manual charge"
    user_id: int | None = None


class ChargeResponse(Schema):
    message: str
    charged_amount: float
    remaining_balance: float
