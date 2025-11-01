from ninja import Schema


class PrinterCreateSchema(Schema):
    name: str
    is_color: bool
    simplex_charge: float | None = None
    duplex_charge: float | None = None


class PrinterOutSchema(PrinterCreateSchema):
    id: int
    image_url: str | None = None


class PrinterDeleteSchema(Schema):
    id: int
    message: str
