from ninja import Schema


class PrinterArrangementCreateSchema(Schema):
    color_printer: int | None = None
    bw_printer: int | None = None


class PrinterArrangementOutSchema(PrinterArrangementCreateSchema):
    id: int
    decomissioned: bool


class PrinterArrangementDeleteSchema(Schema):
    id: int
    message: str
