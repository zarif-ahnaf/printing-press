from ninja import Schema


class UserFilter(Schema):
    name: str | None = None
