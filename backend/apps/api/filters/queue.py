from ninja import Schema


class QueueFilter(Schema):
    include_processed: bool | None = None