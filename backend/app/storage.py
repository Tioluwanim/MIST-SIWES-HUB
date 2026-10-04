"""File storage. `local` for development; `s3` works with AWS S3, Cloudflare R2, Supabase, MinIO etc."""
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile

from .config import get_settings

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
               ".csv", ".txt", ".md", ".zip"}
SAFE_KEY = re.compile(r"^[a-f0-9]{32}\.[a-z0-9]{2,5}$")


def validate_url(url: str | None) -> str | None:
    if not url:
        return None
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise HTTPException(422, "URLs must start with http:// or https://")
    return url


async def save_upload(file: UploadFile) -> dict:
    s = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(422, f"File type {ext or '(none)'} is not allowed")
    data = await file.read(s.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {s.max_upload_mb} MB")
    key = f"{uuid.uuid4().hex}{ext}"
    if s.storage_backend == "s3":
        import boto3
        client = boto3.client("s3", region_name=s.s3_region or None, endpoint_url=s.s3_endpoint_url or None)
        client.put_object(Bucket=s.s3_bucket, Key=key, Body=data, ContentType=file.content_type or "application/octet-stream")
    else:
        d = Path(s.upload_dir)
        d.mkdir(parents=True, exist_ok=True)
        (d / key).write_bytes(data)
    return {"name": file.filename, "url": f"/api/files/{key}"}


def read_file(key: str) -> tuple[bytes, str]:
    if not SAFE_KEY.match(key):
        raise HTTPException(404, "File not found")
    s = get_settings()
    if s.storage_backend == "s3":
        import boto3
        client = boto3.client("s3", region_name=s.s3_region or None, endpoint_url=s.s3_endpoint_url or None)
        try:
            obj = client.get_object(Bucket=s.s3_bucket, Key=key)
        except Exception:
            raise HTTPException(404, "File not found")
        return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")
    path = Path(s.upload_dir) / key
    if not path.is_file():
        raise HTTPException(404, "File not found")
    return path.read_bytes(), "application/octet-stream"
