from fastapi import APIRouter, Depends, Response, UploadFile

from ..deps import get_current_user
from ..models import User
from ..storage import read_file, save_upload

router = APIRouter(prefix="/api", tags=["files"])


@router.post("/uploads", status_code=201)
async def upload(file: UploadFile, _: User = Depends(get_current_user)):
    return await save_upload(file)


@router.get("/files/{key}")
def download(key: str, _: User = Depends(get_current_user)):
    data, ctype = read_file(key)
    return Response(content=data, media_type=ctype, headers={"X-Content-Type-Options": "nosniff",
                                                             "Content-Disposition": "attachment"})
