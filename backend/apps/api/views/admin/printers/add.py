from ninja import File, Form, Router, UploadedFile


from ....http import HttpRequest

router = Router(tags=["Admin Printers"])


@router.get("")
def printers_add(
    request,
):
    print("Hello")

    return {}
