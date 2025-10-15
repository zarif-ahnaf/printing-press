from ninja import Schema


class ChargeRequest(Schema):
    amount: float
    description: str = "Manual charge"


class ChargeResponse(Schema):
    message: str
    charged_amount: float
    remaining_balance: float
