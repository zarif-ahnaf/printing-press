from ninja import Schema


class PrinterCreateSchema(Schema):
    name: str
    is_color: bool
    simplex_charge: int
    duplex_charge: int


class PrinterOutSchema(PrinterCreateSchema):
    id: int
    image: str | None = None
    decomissioned: bool


class PrinterDecomissionSchema(Schema):
    id: int
    decomissioned: bool
    message: str


class PrinterDeleteSchema(Schema):
    id: int
    message: str
