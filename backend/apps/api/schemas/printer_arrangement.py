from ninja import Schema


class PrinterArrangementCreateSchema(Schema):
    color_printer: int
    black_and_white_printer: int


class PrinterArrangementOutSchema(PrinterArrangementCreateSchema):
    id: int
    decomissioned: bool

