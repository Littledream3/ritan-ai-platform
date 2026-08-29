from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import re
import subprocess
import uuid
from datetime import date, datetime
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuditLog, CollectionSession, Doctor, MediaAsset, Patient
from .security import create_access_token, decode_access_token, hash_password, verify_password


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
DATA_ROOT = ROOT / "data"
MEDIA_ROOT = Path(os.environ.get("COLLECTION_MEDIA_ROOT", ROOT / "data" / "media"))
MAX_PHOTO_BYTES = int(os.environ.get("COLLECTION_MAX_PHOTO_MB", "15")) * 1024 * 1024
MAX_VIDEO_BYTES = int(os.environ.get("COLLECTION_MAX_VIDEO_MB", "200")) * 1024 * 1024
INVITE_CODE = os.environ.get("COLLECTION_INVITE_CODE", "ritanai")

DIETARY_OPTIONS = (
    ("balanced", "饮食规律、种类均衡"),
    ("refined_carbs", "主食或精制碳水偏多"),
    ("high_salt", "高盐、重口味"),
    ("high_fat", "高油、油炸食品较多"),
    ("high_sugar", "甜食或含糖饮料较多"),
    ("low_produce", "蔬菜水果摄入不足"),
    ("processed_food", "外卖或加工食品较多"),
    ("irregular_meals", "三餐不规律、夜宵较多"),
)
DIETARY_CODES = {code for code, _ in DIETARY_OPTIONS}
SEX_OPTIONS = {"male", "female"}
DIABETES_GRADES = {"0", "1", "2", "3", "4", "5"}
PHOTO_ROLES = (
    "foot_top", "foot_bottom", "foot_left", "foot_right", "foot_heel",
    "wound_closeup_1", "wound_closeup_2", "wound_closeup_3", "wound_closeup_4", "wound_closeup_5",
)
VIDEO_ROLES = ("full_foot_360", "wound_local")
ALL_ROLES = PHOTO_ROLES + VIDEO_ROLES
ROLE_LABELS = {
    "foot_top": "全足上方", "foot_bottom": "足底", "foot_left": "足部左侧",
    "foot_right": "足部右侧", "foot_heel": "脚后跟",
    **{f"wound_closeup_{index}": f"创口特写 {index}" for index in range(1, 6)},
    "full_foot_360": "全足 360° 环绕视频", "wound_local": "局部创口多角度视频",
}

for grade in DIABETES_GRADES:
    for media_type in ("images", "videos"):
        (DATA_ROOT / f"grade{grade}" / media_type).mkdir(parents=True, exist_ok=True)
app = FastAPI(title="日坛 AI 医生数据采集系统", version="2.0.0")
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")
bearer = HTTPBearer(auto_error=False)


def normalize_phone(value: str) -> str:
    phone = re.sub(r"[\s-]", "", value.strip())
    if phone.startswith("+86"):
        phone = phone[3:]
    if not re.fullmatch(r"1[3-9]\d{9}", phone):
        raise ValueError("请输入有效的11位手机号")
    return phone


def normalize_optional_text(value: str | None, maximum: int) -> str | None:
    if value is None:
        return None
    value = " ".join(value.strip().split())
    return value[:maximum] or None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z][A-Za-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=50)
    institution: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=80)
    password: str = Field(min_length=10, max_length=72)
    invitation_code: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not (re.search(r"[A-Z]", value) and re.search(r"[a-z]", value) and re.search(r"\d", value) and re.search(r"[^A-Za-z0-9]", value)):
            raise ValueError("密码必须同时包含大小写字母、数字和符号")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=72)


class PatientLookupRequest(BaseModel):
    phone: str = Field(min_length=1, max_length=20)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)


class SessionCreateRequest(BaseModel):
    phone: str = Field(min_length=1, max_length=20)
    admission_id: str = Field(min_length=1, max_length=64)
    patient_name: str | None = Field(default=None, max_length=50)
    age: int = Field(ge=0, le=120)
    sex: str
    dietary_habit: str | None = None
    diabetes_grade: str
    residence: str | None = Field(default=None, max_length=100)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("admission_id")
    @classmethod
    def validate_admission(cls, value: str) -> str:
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_.-]{1,64}", value):
            raise ValueError("住院ID只能包含字母、数字、点、下划线或连字符")
        return value

    @field_validator("patient_name")
    @classmethod
    def validate_patient_name(cls, value: str | None) -> str | None:
        value = normalize_optional_text(value, 50)
        if value and not re.fullmatch(r"[\u4e00-\u9fffA-Za-z·.\- ]{1,50}", value):
            raise ValueError("姓名只能包含中文、英文字母、空格、间隔号、点或连字符")
        return value

    @field_validator("residence")
    @classmethod
    def validate_residence(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 100)

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, value: str) -> str:
        if value not in SEX_OPTIONS:
            raise ValueError("性别选项无效")
        return value

    @field_validator("dietary_habit")
    @classmethod
    def validate_diet(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if value not in DIETARY_CODES:
            raise ValueError("饮食习惯选项无效")
        return value

    @field_validator("diabetes_grade")
    @classmethod
    def validate_grade(cls, value: str) -> str:
        if value not in DIABETES_GRADES:
            raise ValueError("糖尿病等级选项无效")
        return value


def doctor_dict(doctor: Doctor) -> dict:
    return {
        "id": doctor.id, "username": doctor.username, "display_name": doctor.display_name,
        "institution": doctor.institution, "department": doctor.department,
    }


def patient_dict(patient: Patient) -> dict:
    return {
        "id": patient.id, "patient_code": patient.patient_code, "phone": patient.phone,
        "name": patient.name, "age": patient.age, "sex": patient.sex,
        "dietary_habit": patient.dietary_habit, "diabetes_grade": patient.diabetes_grade,
        "residence": patient.residence,
    }


def audit(db: Session, request: Request, doctor_id: int | None, action: str, session_id: str | None = None, details: str | None = None) -> None:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_ip = forwarded or (request.client.host if request.client else None)
    db.add(AuditLog(doctor_id=doctor_id, action=action, session_id=session_id, ip_address=client_ip, details=details))


def current_doctor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Doctor:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        doctor_id = decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="登录状态已失效") from None
    doctor = db.get(Doctor, doctor_id)
    if not doctor or not doctor.is_active:
        raise HTTPException(status_code=401, detail="账号不可用")
    return doctor


def owned_session(db: Session, session_id: str, doctor: Doctor) -> CollectionSession:
    session = db.scalar(select(CollectionSession).where(CollectionSession.id == session_id, CollectionSession.doctor_id == doctor.id))
    if not session:
        raise HTTPException(status_code=404, detail="采集记录不存在")
    return session


def generate_code(db: Session, model, field_name: str, prefix: str) -> str:
    for _ in range(20):
        value = f"{prefix}{datetime.now():%y%m%d}{uuid.uuid4().hex[:8].upper()}"
        field = getattr(model, field_name)
        if not db.scalar(select(model).where(field == value)):
            return value
    raise HTTPException(status_code=503, detail="编号生成失败，请重试")


def session_dict(db: Session, session: CollectionSession, detail: bool = False) -> dict:
    patient = db.get(Patient, session.patient_id)
    doctor = db.get(Doctor, session.doctor_id)
    assets = db.scalars(select(MediaAsset).where(MediaAsset.collection_session_id == session.id).order_by(MediaAsset.id)).all()
    data = {
        "id": session.id, "encounter_code": session.encounter_code, "admission_id": session.admission_id,
        "patient": patient_dict(patient) if patient else None,
        "doctor": doctor_dict(doctor) if doctor else None,
        "phone": session.phone_snapshot, "patient_name": session.patient_name or None, "age": session.age,
        "sex": session.sex, "dietary_habit": session.dietary_habit or None,
        "diabetes_grade": session.diabetes_grade, "residence": session.residence or None,
        "status": session.status,
        "photo_count": sum(asset.kind == "photo" for asset in assets),
        "video_count": sum(asset.kind == "video" for asset in assets),
        "created_at": session.created_at.isoformat(timespec="seconds"),
        "completed_at": session.completed_at.isoformat(timespec="seconds") if session.completed_at else None,
    }
    if detail:
        data["media"] = [{
            "role": asset.role, "label": ROLE_LABELS[asset.role], "kind": asset.kind,
            "file_size": asset.file_size, "duration_seconds": asset.duration_seconds,
            "width": asset.width, "height": asset.height,
            "content_url": f"api/sessions/{session.id}/media/{asset.role}",
            "captured_at": asset.captured_at.isoformat(timespec="seconds"),
        } for asset in assets]
    return data


def validate_image(content: bytes) -> tuple[str, str, int, int]:
    try:
        image = Image.open(io.BytesIO(content)); image.verify()
        image = Image.open(io.BytesIO(content)); width, height = image.size
        image_format = (image.format or "").upper()
    except Exception:
        raise HTTPException(status_code=400, detail="照片文件损坏或格式不受支持") from None
    formats = {"JPEG": (".jpg", "image/jpeg"), "PNG": (".png", "image/png"), "WEBP": (".webp", "image/webp")}
    if image_format not in formats or width < 320 or height < 320:
        raise HTTPException(status_code=400, detail="照片须为 JPEG、PNG 或 WebP，且宽高不低于 320 像素")
    ext, mime = formats[image_format]
    return ext, mime, width, height


def validate_video_header(content: bytes, content_type: str | None) -> tuple[str, str]:
    content_type = (content_type or "").lower()
    if len(content) >= 12 and content[4:8] == b"ftyp":
        return (".mov", "video/quicktime") if content_type == "video/quicktime" else (".mp4", "video/mp4")
    if content.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm", "video/webm"
    raise HTTPException(status_code=400, detail="视频须为 MP4、MOV 或 WebM 格式")


def probe_video_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=20, check=True,
        )
        duration = float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        raise HTTPException(status_code=400, detail="无法读取视频时长，请重新录制") from None
    if duration <= 0 or duration > 15.5:
        raise HTTPException(status_code=400, detail="视频时长必须在 15 秒以内")
    return round(duration, 2)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.scalar(select(func.count(Doctor.id)))
    return {"status": "ok", "service": "ritan-dfu-collection", "database": "isolated", "version": "2.0"}


@app.post("/api/auth/register")
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if not hmac.compare_digest(payload.invitation_code, INVITE_CODE):
        raise HTTPException(status_code=403, detail="引荐码无效")
    username = payload.username.lower()
    if db.scalar(select(Doctor).where(Doctor.username == username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    doctor = Doctor(
        username=username, display_name=payload.display_name.strip(),
        institution=normalize_optional_text(payload.institution, 120),
        department=normalize_optional_text(payload.department, 80),
        password_hash=hash_password(payload.password),
    )
    db.add(doctor); db.flush(); audit(db, request, doctor.id, "doctor_register"); db.commit()
    return {"access_token": create_access_token(doctor.id), "doctor": doctor_dict(doctor)}


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    doctor = db.scalar(select(Doctor).where(Doctor.username == payload.username.lower()))
    if not doctor or not doctor.is_active or not verify_password(payload.password, doctor.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    audit(db, request, doctor.id, "doctor_login"); db.commit()
    return {"access_token": create_access_token(doctor.id), "doctor": doctor_dict(doctor)}


@app.get("/api/auth/me")
def me(doctor: Doctor = Depends(current_doctor)):
    return {"doctor": doctor_dict(doctor)}


@app.get("/api/options")
def options(doctor: Doctor = Depends(current_doctor)):
    return {"dietary_habits": [{"code": code, "label": label} for code, label in DIETARY_OPTIONS]}


@app.post("/api/patients/lookup")
def lookup_patient(payload: PatientLookupRequest, db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    patient = db.scalar(select(Patient).where(Patient.phone == payload.phone))
    if not patient:
        return {"found": False, "patient": None, "recent_sessions": []}
    sessions = db.scalars(
        select(CollectionSession).where(CollectionSession.patient_id == patient.id).order_by(CollectionSession.created_at.desc()).limit(10)
    ).all()
    return {"found": True, "patient": patient_dict(patient), "recent_sessions": [session_dict(db, item) for item in sessions]}


def apply_profile(patient: Patient, payload: SessionCreateRequest) -> None:
    patient.phone = payload.phone
    patient.name = payload.patient_name
    patient.age = payload.age
    patient.sex = payload.sex
    patient.dietary_habit = payload.dietary_habit
    patient.diabetes_grade = payload.diabetes_grade
    patient.residence = payload.residence
    patient.updated_at = datetime.now()


@app.post("/api/sessions")
def create_session(payload: SessionCreateRequest, request: Request, db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    if db.scalar(select(CollectionSession).where(CollectionSession.admission_id == payload.admission_id)):
        raise HTTPException(status_code=409, detail="该住院ID已存在，请在工作台查询并打开原记录")
    patient = db.scalar(select(Patient).where(Patient.phone == payload.phone))
    patient_created = patient is None
    if patient is None:
        patient = Patient(patient_code=generate_code(db, Patient, "patient_code", "RT-P"), created_at=datetime.now(), updated_at=datetime.now())
        db.add(patient); db.flush()
    apply_profile(patient, payload)
    session = CollectionSession(
        id=str(uuid.uuid4()), encounter_code=generate_code(db, CollectionSession, "encounter_code", "RT-E"),
        admission_id=payload.admission_id, patient_id=patient.id, doctor_id=doctor.id,
        phone_snapshot=payload.phone, patient_name=payload.patient_name or "", age=payload.age,
        sex=payload.sex, dietary_habit=payload.dietary_habit or "", diabetes_grade=payload.diabetes_grade,
        residence=payload.residence or "",
    )
    db.add(session); audit(db, request, doctor.id, "collection_create", session.id, patient.patient_code); db.commit()
    return {"session": session_dict(db, session, detail=True), "patient_created": patient_created}


@app.put("/api/sessions/{session_id}")
def update_session(session_id: str, payload: SessionCreateRequest, request: Request, db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    session = owned_session(db, session_id, doctor)
    if session.status == "completed":
        raise HTTPException(status_code=409, detail="已归档记录不能修改")
    duplicate = db.scalar(select(CollectionSession).where(CollectionSession.admission_id == payload.admission_id, CollectionSession.id != session.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="该住院ID已被其他记录使用")
    patient = db.get(Patient, session.patient_id)
    other_phone = db.scalar(select(Patient).where(Patient.phone == payload.phone, Patient.id != patient.id))
    if other_phone:
        raise HTTPException(status_code=409, detail="该手机号属于其他患者档案")
    apply_profile(patient, payload)
    session.admission_id = payload.admission_id; session.phone_snapshot = payload.phone
    session.patient_name = payload.patient_name or ""; session.age = payload.age; session.sex = payload.sex
    session.dietary_habit = payload.dietary_habit or ""; session.diabetes_grade = payload.diabetes_grade
    session.residence = payload.residence or ""
    audit(db, request, doctor.id, "collection_update", session.id); db.commit()
    return {"session": session_dict(db, session, detail=True)}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    base = CollectionSession.doctor_id == doctor.id
    total = db.scalar(select(func.count(CollectionSession.id)).where(base)) or 0
    completed = db.scalar(select(func.count(CollectionSession.id)).where(base, CollectionSession.status == "completed")) or 0
    today_count = db.scalar(select(func.count(CollectionSession.id)).where(base, func.date(CollectionSession.created_at) == date.today())) or 0
    patients = db.scalar(select(func.count(func.distinct(CollectionSession.patient_id))).where(base)) or 0
    recent = db.scalars(select(CollectionSession).where(base).order_by(CollectionSession.created_at.desc()).limit(20)).all()
    return {"summary": {"patients": patients, "sessions": total, "completed": completed, "today": today_count}, "sessions": [session_dict(db, item) for item in recent]}


@app.get("/api/workbench")
def workbench(query: str = "", status: str = "all", db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    statement = select(CollectionSession).join(Patient, Patient.id == CollectionSession.patient_id).where(CollectionSession.doctor_id == doctor.id)
    if status in {"collecting", "completed"}:
        statement = statement.where(CollectionSession.status == status)
    query = query.strip()
    if query:
        phone = re.sub(r"[\s-]", "", query)
        if phone.startswith("+86"):
            phone = phone[3:]
        normalized = query.upper()
        statement = statement.where(or_(
            Patient.patient_code == normalized, Patient.phone == phone,
            CollectionSession.admission_id == normalized, CollectionSession.encounter_code == normalized,
        ))
    rows = db.scalars(statement.order_by(CollectionSession.created_at.desc()).limit(100)).all()
    return {"sessions": [session_dict(db, item) for item in rows]}


@app.get("/api/patient-timeline")
def patient_timeline(phone: str = "", db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    try:
        phone = normalize_phone(phone)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    patient_id = db.scalar(
        select(CollectionSession.patient_id)
        .join(Patient, Patient.id == CollectionSession.patient_id)
        .where(
            CollectionSession.doctor_id == doctor.id,
            Patient.phone == phone,
        )
        .limit(1)
    )
    if patient_id is None:
        raise HTTPException(status_code=404, detail="未找到该患者的采集记录")
    patient = db.get(Patient, patient_id)
    rows = db.scalars(
        select(CollectionSession)
        .where(CollectionSession.patient_id == patient_id, CollectionSession.doctor_id == doctor.id)
        .order_by(CollectionSession.created_at.desc())
        .limit(50)
    ).all()
    return {"patient": patient_dict(patient), "sessions": [session_dict(db, row, detail=True) for row in rows]}


@app.get("/api/sessions")
def list_sessions(db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    rows = db.scalars(select(CollectionSession).where(CollectionSession.doctor_id == doctor.id).order_by(CollectionSession.created_at.desc()).limit(100)).all()
    return {"sessions": [session_dict(db, row) for row in rows]}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    return {"session": session_dict(db, owned_session(db, session_id, doctor), detail=True)}


@app.get("/api/sessions/{session_id}/media/{role}")
def read_media(
    session_id: str, role: str,
    db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor),
):
    session = owned_session(db, session_id, doctor)
    asset = db.scalar(select(MediaAsset).where(
        MediaAsset.collection_session_id == session.id, MediaAsset.role == role,
    ))
    if not asset:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    media_root = DATA_ROOT.resolve()
    file_path = (media_root / asset.storage_path).resolve()
    try:
        file_path.relative_to(media_root)
    except ValueError:
        raise HTTPException(status_code=404, detail="媒体文件不存在") from None
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    return FileResponse(file_path, media_type=asset.mime_type, headers={"Cache-Control": "private, max-age=300"})


@app.put("/api/sessions/{session_id}/media/{role}")
async def upload_media(
    session_id: str, role: str, request: Request, file: UploadFile = File(...),
    db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor),
):
    session = owned_session(db, session_id, doctor)
    if session.status == "completed":
        raise HTTPException(status_code=409, detail="该记录已经归档")
    if role not in ALL_ROLES:
        raise HTTPException(status_code=404, detail="采集项目不存在")
    kind = "photo" if role in PHOTO_ROLES else "video"
    limit = MAX_PHOTO_BYTES if kind == "photo" else MAX_VIDEO_BYTES
    content = await file.read(limit + 1)
    if not content or len(content) > limit:
        raise HTTPException(status_code=413, detail=f"文件不能为空且不得超过 {limit // 1024 // 1024} MB")
    width = height = None; duration = None
    if kind == "photo":
        ext, mime_type, width, height = validate_image(content)
    else:
        ext, mime_type = validate_video_header(content, file.content_type)
    media_type_dir = "images" if kind == "photo" else "videos"
    session_dir = DATA_ROOT / f"grade{session.diabetes_grade}" / media_type_dir / session.id
    session_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{role}-{uuid.uuid4().hex}{ext}"
    final_path = session_dir / stored_name; temporary_path = session_dir / f".{stored_name}.part"
    temporary_path.write_bytes(content)
    try:
        if kind == "video":
            duration = probe_video_duration(temporary_path)
        temporary_path.replace(final_path)
        existing = db.scalar(select(MediaAsset).where(MediaAsset.collection_session_id == session.id, MediaAsset.role == role))
        old_path = DATA_ROOT / existing.storage_path if existing else None
        values = {
            "kind": kind, "original_filename": (file.filename or stored_name)[:255],
            "storage_path": str(final_path.relative_to(DATA_ROOT)).replace("\\", "/"),
            "mime_type": mime_type, "file_size": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "width": width, "height": height, "duration_seconds": duration, "captured_at": datetime.now(),
        }
        if existing:
            for key, value in values.items(): setattr(existing, key, value)
            asset = existing
        else:
            asset = MediaAsset(collection_session_id=session.id, role=role, **values); db.add(asset)
        audit(db, request, doctor.id, "media_upload", session.id, f"{role}:{len(content)}"); db.commit()
        if old_path and old_path != final_path: old_path.unlink(missing_ok=True)
    except Exception:
        db.rollback(); temporary_path.unlink(missing_ok=True); final_path.unlink(missing_ok=True); raise
    return {"media": {"role": asset.role, "label": ROLE_LABELS[asset.role], "kind": asset.kind, "file_size": asset.file_size, "duration_seconds": asset.duration_seconds}}


@app.post("/api/sessions/{session_id}/complete")
def complete_session(session_id: str, request: Request, db: Session = Depends(get_db), doctor: Doctor = Depends(current_doctor)):
    session = owned_session(db, session_id, doctor)
    if session.status == "completed":
        return {"session": session_dict(db, session, detail=True), "already_completed": True}
    roles = set(db.scalars(select(MediaAsset.role).where(MediaAsset.collection_session_id == session.id)).all())
    missing_photos = [ROLE_LABELS[role] for role in PHOTO_ROLES if role not in roles]
    missing_fields = []
    if not session.phone_snapshot: missing_fields.append("手机号")
    if session.age is None: missing_fields.append("年龄")
    if not session.sex: missing_fields.append("性别")
    if not session.diabetes_grade: missing_fields.append("糖尿病等级")
    if missing_fields or missing_photos:
        raise HTTPException(status_code=409, detail={
            "message": "请补充必填内容后再提交", "missing_fields": missing_fields, "missing_photos": missing_photos,
        })
    session.status = "completed"; session.completed_at = datetime.now()
    audit(db, request, doctor.id, "collection_complete", session.id, f"10 photos, {len(roles.intersection(VIDEO_ROLES))} optional videos")
    db.commit()
    return {"session": session_dict(db, session, detail=True), "already_completed": False}
