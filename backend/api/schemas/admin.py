from ninja import Schema


class AdminDepositPayload(Schema):
    user_id: int
    amount: str
    description: str | None = None


class AdminUploadPayload(Schema):
    user_id: int
