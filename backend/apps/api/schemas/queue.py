from datetime import datetime

from ninja import Schema


class QueueFileUpload(Schema):
    user_id: int | None = None


class QueueFileResponse(Schema):
    id: int
    file: str
    processed: bool
    created_at: datetime
    user: str


class QueueUploadResponse(Schema):
    message: str
    total_pages: int
    queue_ids: list[int]
    total_charged_bdt: str


class QueueListResponse(Schema):
    queue: list[QueueFileResponse]


class ProcessStatusResponse(Schema):
    id: int
    processed: bool
    message: str
