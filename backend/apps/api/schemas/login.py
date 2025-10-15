from ninja import Schema


class LoginInSchema(Schema):
    username: str
    password: str


class LoginOutSchema(Schema):
    token: str
