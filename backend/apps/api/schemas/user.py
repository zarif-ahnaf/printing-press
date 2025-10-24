import datetime

from ninja import Schema


class UserSchema(Schema):
    id: int
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool
    is_staff: bool
    is_superuser: bool
    date_joined: datetime.datetime
