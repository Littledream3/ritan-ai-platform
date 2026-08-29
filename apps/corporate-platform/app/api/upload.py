"""文件上传 API — 提取文本内容供模型处理"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from loguru import logger

from app.core.config import settings
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["文件上传"])

# 纯文本文件扩展名（直接读取）
TEXT_EXTS = {".txt", ".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".csv", ".xml", ".yaml",
             ".yml", ".toml", ".ini", ".cfg", ".conf", ".md", ".rst", ".sh", ".bash",
             ".html", ".css", ".scss", ".less", ".sql", ".log", ".env", ".java", ".c",
             ".cpp", ".h", ".hpp", ".rs", ".go", ".rb", ".php", ".swift", ".kt", ".r",
             ".m", ".mm", ".lua", ".vim", ".tex", ".bib"}

# 需要解析的文档扩展名
PDF_EXT = ".pdf"

# 视频扩展名
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """上传文件，提取文本内容"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = os.path.splitext(file.filename)[1].lower()
    content_bytes = await file.read()
    file_size = len(content_bytes)

    # 限制大小（使用配置）
    max_size = settings.upload_max_file_size
    if file_size > max_size:
        raise HTTPException(status_code=400, detail=f"文件大小不能超过 {max_size // 1024 // 1024}MB")

    try:
        # 纯文本文件
        if ext in TEXT_EXTS:
            text = content_bytes.decode("utf-8")
            return {
                "filename": file.filename,
                "size": file_size,
                "type": "text",
                "content": text,
            }

        # PDF 文件
        if ext == PDF_EXT:
            text = _extract_pdf(content_bytes)
            return {
                "filename": file.filename,
                "size": file_size,
                "type": "pdf",
                "content": text,
            }

        # DOCX 文件
        if ext == ".docx":
            text = _extract_docx(content_bytes)
            return {
                "filename": file.filename,
                "size": file_size,
                "type": "docx",
                "content": text,
            }

        # 其他文件类型 — 尝试当文本读
        try:
            text = content_bytes.decode("utf-8")
            return {
                "filename": file.filename,
                "size": file_size,
                "type": "text",
                "content": text,
            }
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型 ({ext})，支持的格式: 文本文件、PDF、DOCX、图片(直接粘贴)、视频(请用 /upload/video)",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件解析失败: {file.filename} — {e}")
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")


def _extract_pdf(data: bytes) -> str:
    """从 PDF 字节中提取文本"""
    try:
        from PyPDF2 import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(data))
        parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                parts.append(text)
            if len(parts) > 50:  # 最多 50 页
                break

        result = "\n\n".join(parts)
        if not result.strip():
            return "[PDF 文件，无法提取文字（可能是扫描件或图片型 PDF）]"
        return result
    except ImportError:
        return "[PyPDF2 未安装，无法解析 PDF。请联系管理员安装 PyPDF2。]"


def _extract_docx(data: bytes) -> str:
    """从 DOCX 字节中提取文本"""
    try:
        from docx import Document
        from io import BytesIO

        doc = Document(BytesIO(data))
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        return "\n".join(parts)
    except ImportError:
        return "[python-docx 未安装，无法解析 DOCX。请联系管理员安装。]"


@router.post("/upload/video")
async def upload_video(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """上传视频文件，保存到 static/videos/ 并返回 URL"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in VIDEO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的视频格式 ({ext})，支持: {', '.join(VIDEO_EXTS)}",
        )

    # 校验 MIME type
    if file.content_type and not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail=f"不是有效的视频文件 (MIME: {file.content_type})",
        )

    # 读取并保存
    content_bytes = await file.read()
    file_size = len(content_bytes)

    max_size = settings.upload_max_video_size
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"视频大小不能超过 {max_size // 1024 // 1024}MB",
        )

    # 确保目录存在
    videos_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "static", "videos"
    )
    os.makedirs(videos_dir, exist_ok=True)

    # UUID 文件名
    saved_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(videos_dir, saved_name)

    try:
        with open(save_path, "wb") as f:
            f.write(content_bytes)
    except OSError as e:
        logger.error(f"视频保存失败: {save_path} — {e}")
        raise HTTPException(status_code=500, detail=f"视频保存失败: {str(e)}")

    url = f"/static/videos/{saved_name}"
    logger.info(f"📹 用户 {user.username} 上传视频: {file.filename} → {url} ({file_size} bytes)")

    return {
        "filename": file.filename,
        "size": file_size,
        "url": url,
    }
