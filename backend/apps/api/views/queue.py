from ninja import Router, File
from ninja.files import UploadedFile

router = Router(tags=["Queue"])


@router.post("/nonblank")
def queue_files(
    request,
    file: File[UploadedFile],
):
    return "ok"
