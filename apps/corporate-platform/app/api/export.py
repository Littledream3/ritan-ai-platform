"""导出 API — docx/pdf/xlsx 文件下载"""

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.export_service import export_document

router = APIRouter(prefix="/api/v1", tags=["导出"])


class ExportRequest(BaseModel):
    content: str = ""
    format: str = Field(default="docx", pattern="^(docx|pdf|xlsx)$")
    title: str = ""
    type: str = ""
    rows: list[dict] | None = None


@router.post("/export")
async def export(
    body: ExportRequest,
    user: User = Depends(get_current_user),
):
    """导出内容为 docx/pdf/xlsx 文件"""
    try:
        file_bytes, media_type, filename = await export_document(
            content=body.content,
            fmt=body.format,
            title=body.title,
            doc_type=body.type,
            rows=body.rows,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")

    return StreamingResponse(
        BytesIO(file_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )
