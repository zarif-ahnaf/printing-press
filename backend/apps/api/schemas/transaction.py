from ninja import Schema

class TransactionResponse(Schema):
    id: int
    transaction_type: str
    amount: str
    description: str
    created_at: str
