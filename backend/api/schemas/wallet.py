from ninja import Schema
from typing import List, Optional, Union


class PDFUploadResult(Schema):
    filename: str
    total_pages: int
    non_blank_pages: int
    blank_pages: int
    charge_taka: int


class PDFUploadError(Schema):
    filename: Optional[str] = None
    error: str


class UploadSuccessResponse(Schema):
    uploads: List[Union[PDFUploadResult, PDFUploadError]]
    total_files_processed: int
    total_charge_taka: int
    remaining_balance: float
    message: str


class UploadNoChargeResponse(Schema):
    uploads: List[Union[PDFUploadResult, PDFUploadError]]
    total_charge_taka: int
    message: str


class ErrorResponse(Schema):
    detail: str
    current_balance: Optional[float] = None
    required: Optional[int] = None
