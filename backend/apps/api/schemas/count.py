from ninja import Schema


class PDFPageCountOut(Schema):
    page_count: int
    filename: str
