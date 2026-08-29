from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import shutil
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import MediaFile, UploadBatch

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
UPLOAD_ROOT = Path(os.environ.get("MEDIA_DROP_ROOT", ROOT / "data" / "uploads"))
MAX_PHOTO_BYTES = int(os.environ.get("MEDIA_DROP_MAX_PHOTO_MB", "25")) * 1024 * 1024
MAX_VIDEO_BYTES = int(os.environ.get("MEDIA_DROP_MAX_VIDEO_MB", "750")) * 1024 * 1024
MAX_BATCH_FILES = int(os.environ.get("MEDIA_DROP_MAX_BATCH_FILES", "500"))
MAX_BATCH_GB = float(os.environ.get("MEDIA_DROP_MAX_BATCH_GB", "20"))
MAX_BATCH_BYTES = int(MAX_BATCH_GB * 1024**3)
DISK_RESERVE_BYTES = int(float(os.environ.get("MEDIA_DROP_DISK_RESERVE_GB", "10")) * 1024**3)
MAX_BATCHES_PER_IP_HOUR = 20
CHUNK_SIZE = 1024 * 1024
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}

UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="日坛 AI 快速媒体上传", version="1.0.0")
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response


def client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def load_batch(db: Session, batch_id: str, token: str | None, lock: bool = False) -> UploadBatch:
    if not token or len(token) > 200:
        raise HTTPException(status_code=401, detail="上传批次凭证缺失")
    query = select(UploadBatch).where(UploadBatch.id == batch_id)
    if lock:
        query = query.with_for_update()
    batch = db.scalar(query)
    if not batch or not hmac.compare_digest(batch.upload_token_hash, token_hash(token)):
        raise HTTPException(status_code=403, detail="上传批次凭证无效")
    if batch.status == "open" and batch.created_at < datetime.now() - timedelta(hours=24):
        batch.status = "expired"
        db.commit()
    if batch.status == "expired":
        raise HTTPException(status_code=410, detail="该上传批次已过期")
    return batch


def ensure_disk_capacity(incoming_bytes: int = 0) -> None:
    free = shutil.disk_usage(UPLOAD_ROOT).free
    if free - incoming_bytes < DISK_RESERVE_BYTES:
        raise HTTPException(status_code=507, detail="服务器可用空间不足，请联系管理员")


def clean_original_name(filename: str | None) -> str:
    value = Path(filename or "unnamed").name
    value = "".join(character for character in value if ord(character) >= 32).strip()
    return (value or "unnamed")[:255]


def validate_image(path: Path) -> tuple[str, str, int, int] | None:
    try:
        image = Image.open(path)
        image.verify()
        image = Image.open(path)
        width, height = image.size
        image_format = (image.format or "").upper()
    except Exception:
        return None
    formats = {"JPEG": (".jpg", "image/jpeg"), "PNG": (".png", "image/png"), "WEBP": (".webp", "image/webp"), "HEIF": (".heif", "image/heif")}
    if image_format not in formats or width < 64 or height < 64:
        return None
    extension, mime_type = formats[image_format]
    return extension, mime_type, width, height


def validate_video(path: Path, supplied_type: str | None) -> tuple[str, str, float] | None:
    with path.open("rb") as handle:
        header = handle.read(32)
    if len(header) >= 12 and header[4:8] == b"ftyp":
        extension = ".mov" if (supplied_type or "").lower() == "video/quicktime" else ".mp4"
        mime_type = "video/quicktime" if extension == ".mov" else "video/mp4"
    elif header.startswith(b"\x1a\x45\xdf\xa3"):
        extension, mime_type = ".webm", "video/webm"
    else:
        return None
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        duration = float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return None
    if duration <= 0:
        return None
    return extension, mime_type, round(duration, 2)


def batch_dict(batch: UploadBatch, files: list[MediaFile] | None = None) -> dict:
    data = {
        "id": batch.id,
        "status": batch.status,
        "file_count": batch.file_count,
        "total_bytes": batch.total_bytes,
        "created_at": batch.created_at.isoformat(timespec="seconds"),
        "completed_at": batch.completed_at.isoformat(timespec="seconds") if batch.completed_at else None,
    }
    if files is not None:
        data["files"] = [
            {
                "id": item.id,
                "name": item.original_filename,
                "kind": item.kind,
                "size": item.file_size,
                "width": item.width,
                "height": item.height,
                "duration_seconds": item.duration_seconds,
            }
            for item in files
        ]
    return data


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.scalar(select(func.count(UploadBatch.id)))
    return {"status": "ok", "service": "ritan-media-drop", "database": "isolated"}


@app.post("/api/batches")
def create_batch(request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    recent = db.scalar(
        select(func.count(UploadBatch.id)).where(
            UploadBatch.source_ip == ip,
            UploadBatch.created_at >= datetime.now() - timedelta(hours=1),
        )
    ) or 0
    if recent >= MAX_BATCHES_PER_IP_HOUR:
        raise HTTPException(status_code=429, detail="创建批次过于频繁，请稍后再试")
    ensure_disk_capacity()
    token = secrets.token_urlsafe(32)
    batch = UploadBatch(
        id=str(uuid.uuid4()),
        upload_token_hash=token_hash(token),
        source_ip=ip,
        user_agent=(request.headers.get("user-agent") or "")[:255],
    )
    db.add(batch)
    db.commit()
    return {
        "batch": batch_dict(batch),
        "upload_token": token,
        "limits": {
            "max_files": MAX_BATCH_FILES,
            "max_batch_bytes": MAX_BATCH_BYTES,
            "max_photo_bytes": MAX_PHOTO_BYTES,
            "max_video_bytes": MAX_VIDEO_BYTES,
        },
    }


@app.get("/api/batches/{batch_id}")
def get_batch(
    batch_id: str,
    x_upload_token: str | None = Header(None),
    db: Session = Depends(get_db),
):
    batch = load_batch(db, batch_id, x_upload_token)
    files = db.scalars(select(MediaFile).where(MediaFile.upload_batch_id == batch.id).order_by(MediaFile.id)).all()
    return {"batch": batch_dict(batch, list(files))}


@app.post("/api/batches/{batch_id}/files")
async def upload_file(
    batch_id: str,
    file: UploadFile = File(...),
    x_upload_token: str | None = Header(None),
    db: Session = Depends(get_db),
):
    batch = load_batch(db, batch_id, x_upload_token)
    if batch.status != "open":
        raise HTTPException(status_code=409, detail="该批次已经完成，不能继续上传")
    if batch.file_count >= MAX_BATCH_FILES:
        raise HTTPException(status_code=413, detail=f"单批最多上传 {MAX_BATCH_FILES} 个文件")

    supplied_name = clean_original_name(file.filename)
    supplied_extension = Path(supplied_name).suffix.lower()
    supplied_type = (file.content_type or "").lower()
    probable_video = supplied_type.startswith("video/") or supplied_extension in VIDEO_EXTENSIONS
    per_file_limit = MAX_VIDEO_BYTES if probable_video else MAX_PHOTO_BYTES
    ensure_disk_capacity(per_file_limit)

    batch_dir = UPLOAD_ROOT / batch.id
    batch_dir.mkdir(parents=True, exist_ok=True)
    temporary = batch_dir / f".{uuid.uuid4().hex}.part"
    final_path: Path | None = None
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary.open("wb") as output:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > per_file_limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过 {'750 MB' if probable_video else '25 MB'} 限制",
                    )
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="不能上传空文件")
        if batch.total_bytes + size > MAX_BATCH_BYTES:
            raise HTTPException(status_code=413, detail=f"单批文件总大小不能超过 {MAX_BATCH_GB:g} GB")
        ensure_disk_capacity(size)

        image_info = validate_image(temporary)
        duration = None
        if image_info:
            extension, mime_type, width, height = image_info
            kind = "image"
            if size > MAX_PHOTO_BYTES:
                raise HTTPException(status_code=413, detail="图片不能超过 25 MB")
        else:
            video_info = validate_video(temporary, supplied_type)
            if not video_info:
                raise HTTPException(status_code=400, detail="仅支持有效的 JPEG、PNG、WebP、MP4、MOV 或 WebM 文件")
            extension, mime_type, duration = video_info
            width = height = None
            kind = "video"
            if size > MAX_VIDEO_BYTES:
                raise HTTPException(status_code=413, detail="视频不能超过 750 MB")

        sha256 = digest.hexdigest()
        if db.scalar(select(MediaFile.id).where(MediaFile.upload_batch_id == batch.id, MediaFile.sha256 == sha256)):
            raise HTTPException(status_code=409, detail="该文件已在本批次中上传")

        stored_name = f"{uuid.uuid4().hex}{extension}"
        final_path = batch_dir / stored_name
        temporary.replace(final_path)
        locked_batch = load_batch(db, batch_id, x_upload_token, lock=True)
        if locked_batch.status != "open" or locked_batch.file_count >= MAX_BATCH_FILES or locked_batch.total_bytes + size > MAX_BATCH_BYTES:
            final_path.unlink(missing_ok=True)
            raise HTTPException(status_code=409, detail="批次状态或容量已发生变化，请刷新后重试")
        media = MediaFile(
            upload_batch_id=locked_batch.id,
            kind=kind,
            original_filename=supplied_name,
            storage_path=str(final_path.relative_to(UPLOAD_ROOT)).replace("\\", "/"),
            mime_type=mime_type,
            file_size=size,
            sha256=sha256,
            width=width,
            height=height,
            duration_seconds=duration,
        )
        db.add(media)
        locked_batch.file_count += 1
        locked_batch.total_bytes += size
        locked_batch.last_activity_at = datetime.now()
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            final_path.unlink(missing_ok=True)
            raise HTTPException(status_code=409, detail="该文件已在本批次中上传") from None
    except Exception:
        db.rollback()
        temporary.unlink(missing_ok=True)
        if final_path is not None:
            final_path.unlink(missing_ok=True)
        raise
    return {"file": {"id": media.id, "name": media.original_filename, "kind": media.kind, "size": media.file_size, "duration_seconds": media.duration_seconds}}


@app.post("/api/batches/{batch_id}/complete")
def complete_batch(
    batch_id: str,
    x_upload_token: str | None = Header(None),
    db: Session = Depends(get_db),
):
    batch = load_batch(db, batch_id, x_upload_token, lock=True)
    if batch.status == "completed":
        return {"batch": batch_dict(batch)}
    if batch.file_count == 0:
        raise HTTPException(status_code=409, detail="尚未上传任何文件")
    batch.status = "completed"
    batch.completed_at = datetime.now()
    batch.last_activity_at = datetime.now()
    db.commit()
    return {"batch": batch_dict(batch)}
