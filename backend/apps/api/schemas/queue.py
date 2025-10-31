from typing import Literal, Optional

from ninja import Schema


class QueueFileUpload(Schema):
    user_id: Optional[int] = None


class QueueFileResponse(Schema):
    id: int
    file: str
    processed: bool
    created_at: str
    user: str
    user_id: int
    page_count: Optional[int]


class QueueListResponse(Schema):
    queue: list[QueueFileResponse]


class QueueUploadResponse(Schema):
    message: str
    total_pages: int
    queue_ids: list[int]
    total_charged_bdt: str


class ProcessStatusResponse(Schema):
    id: int
    processed: bool
    message: str


class QueueDeleteResponse(Schema):
    id: int
    message: str


class ChangePrintModeRequest(Schema):
    page_type: Literal["single-sided", "double-sided"]


class ChangeProcessStatusResponse(Schema):
    id: int
    message: str
