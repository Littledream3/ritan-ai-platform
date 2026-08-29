# -*- coding: utf-8 -*-
"""DFU patient and doctor portal API."""
from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import os
import random
import re
import subprocess
import sys
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
import uvicorn
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image as PILImage
from PIL import ImageOps
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session


mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("application/wasm", ".wasm")

CODE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE_ROOT))

from auth import (  # noqa: E402
    MAX_VERIFY_ATTEMPTS,
    RESEND_COOLDOWN_SECONDS,
    create_jwt,
    decode_jwt,
    hash_password,
    send_email_code,
    validate_email,
    validate_password,
    verify_password,
)
from database import (  # noqa: E402
    AnalysisRecord,
    AnalysisRecordImage,
    AuditLog,
    ClinicalEncounter,
    ClinicalVideo,
    ConsentRecord,
    DietaryHabitOption,
    DoctorPatientLink,
    DoctorProfile,
    FollowUpPlan,
    LeadSubmission,
    PartnerInstitution,
    ReferralRecord,
    EmailVerifyCode,
    InvitationCode,
    MedicalImage,
    PatientDietaryHabit,
    PatientProfile,
    User,
    get_db,
    init_db,
)
from recommend import format_report, get_recommendations  # noqa: E402
from report_pdf import build_assessment_report  # noqa: E402


FRONTEND_DIR = CODE_ROOT.parent / "frontend"
UPLOADS_DIR = CODE_ROOT / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DOCTOR_CREDENTIALS_DIR = CODE_ROOT / "doctor_credentials"
DOCTOR_CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
GRADE_STORAGE_DIRS = {
    "Normal": "normal",
    "Grade 0": "grade0",
    "Grade 1": "grade1",
    "Grade 2": "grade2",
    "Grade 3": "grade3",
    "Grade 4": "grade4",
    "Grade 5": "grade5",
}
for _grade_dir in GRADE_STORAGE_DIRS.values():
    for _media_dir in ("images", "videos"):
        (UPLOADS_DIR / _grade_dir / _media_dir).mkdir(parents=True, exist_ok=True)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/bmp", "image/webp"}
MAX_UPLOAD_BYTES = int(os.getenv("DFU_MAX_UPLOAD_MB", "10")) * 1024 * 1024
MAX_IMAGE_PIXELS = int(os.getenv("DFU_MAX_IMAGE_PIXELS", "25000000"))
MAX_VIDEO_BYTES = int(os.getenv("DFU_MAX_VIDEO_MB", "100")) * 1024 * 1024
MAX_VIDEO_SECONDS = int(os.getenv("DFU_MAX_VIDEO_SECONDS", "15"))
VIDEO_ROLES = {"full_foot_video": "全足环绕视频", "wound_video": "创口局部视频"}
CAPTURE_ROLES = (
    ("left_view", "左侧视角"),
    ("right_view", "右侧视角"),
    ("plantar_view", "足底视角"),
    ("wound_closeup_1", "最严重创口特写一"),
    ("wound_closeup_2", "最严重创口特写二"),
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if os.getenv("DFU_SKIP_MODEL_PRELOAD") != "1":
        try:
            from model_v2 import load_model

            load_model()
            print("[DFU Server] ConvNeXt+CORN 模型加载完成，服务已就绪。")
        except Exception as exc:
            print(f"[DFU Server] 模型预加载失败，将在首次推理时重试: {exc}")
    yield


app = FastAPI(title="DFU 糖尿病足溃疡智能分级系统", version="2.0.0", lifespan=lifespan)
cors_origins = [item.strip() for item in os.getenv("DFU_CORS_ORIGINS", "").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=bool(cors_origins),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Authentication dependencies
# ---------------------------------------------------------------------------

def _bearer_payload(authorization: str | None) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return decode_jwt(authorization[7:])


def get_optional_user(
    authorization: str | None = Header(None), db: Session = Depends(get_db)
) -> User | None:
    payload = _bearer_payload(authorization)
    if not payload:
        return None
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None
    user = db.get(User, user_id)
    return user if user and user.is_active else None


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return user


def get_patient_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "patient":
        raise HTTPException(status_code=403, detail="仅患者账号可以执行此操作")
    return user


def get_doctor_user(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    if user.role not in {"doctor", "admin"}:
        raise HTTPException(status_code=403, detail="仅医生账号可以执行此操作")
    if user.role == "doctor":
        profile = db.get(DoctorProfile, user.id)
        if not profile or profile.verification_status != "approved":
            raise HTTPException(status_code=403, detail="医生资质尚未审核通过")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以执行此操作")
    return user


def _token_response(user: User) -> dict:
    token = create_jwt(
        user.id,
        email=user.email,
        role=user.role,
        username=user.username,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "role": user.role,
            "email": user.email,
            "username": user.username,
        },
    }


def _validate_email_or_400(value: str) -> str:
    try:
        return validate_email(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _validate_password_or_400(value: str) -> str:
    try:
        return validate_password(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _audit(db: Session, request: Request, actor_id: int | None, action: str, **kwargs) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_id,
            action=action,
            target_type=kwargs.get("target_type"),
            target_id=kwargs.get("target_id"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:255],
            details=kwargs.get("details"),
        )
    )


def _new_public_code(db: Session, model, field_name: str, prefix: str) -> str:
    """Create a short, non-sequential public identifier backed by a unique index."""
    field = getattr(model, field_name)
    for _ in range(20):
        code = f"{prefix}-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
        if not db.scalar(select(model).where(field == code)):
            return code
    raise HTTPException(status_code=503, detail="暂时无法生成唯一编号，请稍后重试")


def _normalize_admission_id(value: str) -> str:
    admission_id = value.strip().upper()
    if not 1 <= len(admission_id) <= 64:
        raise HTTPException(status_code=400, detail="住院ID长度应为 1 到 64 个字符")
    if not re.fullmatch(r"[0-9A-Z._/-]+", admission_id):
        raise HTTPException(status_code=400, detail="住院ID只能包含字母、数字、点、横线、下划线或斜线")
    return admission_id


def _normalize_phone(value: str) -> str:
    phone = re.sub(r"[\s-]", "", value.strip())
    if phone.startswith("+86"):
        phone = phone[3:]
    elif phone.startswith("86") and len(phone) == 13:
        phone = phone[2:]
    if not re.fullmatch(r"1[3-9]\d{9}", phone):
        raise HTTPException(status_code=400, detail="请输入有效的11位中国大陆手机号")
    return phone


def _patient_code(db: Session) -> str:
    return _new_public_code(db, PatientProfile, "patient_code", "RT-P")


def _encounter_code(db: Session) -> str:
    return _new_public_code(db, ClinicalEncounter, "encounter_code", "RT-E")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class EmailSendCodeRequest(BaseModel):
    email: str
    purpose: str = "register"


class EmailRegisterRequest(BaseModel):
    email: str
    code: str
    password: str


class EmailLoginRequest(BaseModel):
    email: str
    password: str


class EmailResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


class PatientProfileRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    phone: str = Field(min_length=1, max_length=20)
    age: int = Field(ge=0, le=120)
    sex: str
    diabetes_grade: str | None = None
    residence: str | None = Field(default=None, max_length=200)
    dietary_habits: list[str] = Field(default_factory=list, max_length=8)


class DoctorRegisterRequest(BaseModel):
    username: str = Field(min_length=4, max_length=32)
    real_name: str = Field(min_length=1, max_length=80)
    password: str
    invitation_code: str
    institution: str | None = Field(default=None, max_length=160)
    department: str | None = Field(default=None, max_length=100)
    license_number: str = Field(min_length=3, max_length=100)


class LeadSubmissionRequest(BaseModel):
    lead_type: str = Field(min_length=1, max_length=40)
    organization: str = Field(min_length=1, max_length=160)
    department: str | None = Field(default=None, max_length=100)
    contact_name: str = Field(min_length=1, max_length=80)
    contact_value: str = Field(min_length=3, max_length=120)
    monthly_volume: str | None = Field(default=None, max_length=80)
    cooperation_type: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=2000)


class ReferralRequest(BaseModel):
    patient_id: int
    analysis_record_id: int | None = None
    target_institution: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)


class DoctorLoginRequest(BaseModel):
    username: str
    password: str


class PatientLookupRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20)


class DoctorEncounterDraftRequest(BaseModel):
    admission_id: str = Field(min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=20)
    age: int | None = Field(default=None, ge=0, le=120)
    sex: str | None = None
    diabetes_grade: str | None = None
    residence: str | None = Field(default=None, max_length=200)
    dietary_habits: list[str] = Field(default_factory=list, max_length=8)


class DoctorCreatePatientRequest(DoctorEncounterDraftRequest):
    email: str | None = Field(default=None, max_length=254)



@app.post("/api/public/leads")
async def create_public_lead(req: LeadSubmissionRequest, db: Session = Depends(get_db)):
    allowed = {"institution_trial", "medical_research", "pharma_research", "patient_followup"}
    if req.lead_type not in allowed:
        raise HTTPException(status_code=400, detail="合作类型无效")
    recent_cutoff = datetime.now() - timedelta(minutes=10)
    duplicate = db.scalar(
        select(LeadSubmission).where(
            LeadSubmission.lead_type == req.lead_type,
            LeadSubmission.contact_value == req.contact_value.strip(),
            LeadSubmission.created_at >= recent_cutoff,
        )
    )
    if duplicate:
        return {"success": True, "message": "您的合作意向已收到，请勿重复提交", "lead_id": duplicate.id}
    row = LeadSubmission(
        lead_type=req.lead_type,
        organization=req.organization.strip(),
        department=(req.department or "").strip() or None,
        contact_name=req.contact_name.strip(),
        contact_value=req.contact_value.strip(),
        monthly_volume=(req.monthly_volume or "").strip() or None,
        cooperation_type=(req.cooperation_type or "").strip() or None,
        message=(req.message or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"success": True, "message": "合作意向已提交，我们将在资料接入后安排跟进", "lead_id": row.id}


@app.get("/api/public/partner-institutions")
async def list_partner_institutions(region: str = "", db: Session = Depends(get_db)):
    query = select(PartnerInstitution).where(PartnerInstitution.is_active.is_(True))
    if region.strip():
        query = query.where(PartnerInstitution.region.ilike(f"%{region.strip()}%"))
    rows = db.scalars(query.order_by(PartnerInstitution.sort_order, PartnerInstitution.id)).all()
    return {"institutions": [
        {"id": row.id, "name": row.name, "region": row.region, "department": row.department,
         "address": row.address, "contact_url": row.contact_url}
        for row in rows
    ], "configured": bool(rows)}


@app.get("/api/admin/doctor-verifications")
async def admin_doctor_verifications(
    status: str = "pending", db: Session = Depends(get_db), _: User = Depends(get_admin_user)
):
    query = select(DoctorProfile)
    if status in {"pending", "approved", "rejected"}:
        query = query.where(DoctorProfile.verification_status == status)
    rows = db.scalars(query.order_by(DoctorProfile.created_at.desc())).all()
    return {"doctors": [
        {"user_id": row.user_id, "real_name": row.real_name, "institution": row.institution,
         "department": row.department, "license_number": row.license_number,
         "verification_status": row.verification_status, "verification_note": row.verification_note,
         "created_at": row.created_at.isoformat()}
        for row in rows
    ]}


@app.put("/api/admin/doctor-verifications/{doctor_id}")
async def admin_review_doctor(
    doctor_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)
):
    payload = await request.json()
    status = str(payload.get("status", ""))
    if status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="审核状态必须为 approved 或 rejected")
    profile = db.get(DoctorProfile, doctor_id)
    if not profile:
        raise HTTPException(status_code=404, detail="医生资料不存在")
    profile.verification_status = status
    profile.verification_note = str(payload.get("note", ""))[:500] or None
    profile.verified_at = datetime.now()
    profile.verified_by_user_id = admin.id
    db.commit()
    return {"success": True, "verification_status": status}


@app.get("/api/admin/doctor-verifications/{doctor_id}/credential")
async def admin_download_doctor_credential(
    doctor_id: int, db: Session = Depends(get_db), _: User = Depends(get_admin_user)
):
    profile = db.get(DoctorProfile, doctor_id)
    if not profile or not profile.credential_storage_path:
        raise HTTPException(status_code=404, detail="资质文件不存在")
    path = DOCTOR_CREDENTIALS_DIR / profile.credential_storage_path
    if not path.is_file() or path.parent.resolve() != DOCTOR_CREDENTIALS_DIR.resolve():
        raise HTTPException(status_code=404, detail="资质文件不存在")
    return StreamingResponse(path.open("rb"), media_type="application/octet-stream",
                             headers={"Content-Disposition": f'attachment; filename="{path.name}"'})


# ---------------------------------------------------------------------------
# Patient email authentication
# ---------------------------------------------------------------------------

@app.post("/api/email/send-code")
async def email_send_code(req: EmailSendCodeRequest, db: Session = Depends(get_db)):
    email = _validate_email_or_400(req.email)
    purpose = req.purpose if req.purpose in {"register", "reset"} else "register"
    last = db.scalar(
        select(EmailVerifyCode)
        .where(EmailVerifyCode.email == email, EmailVerifyCode.purpose == purpose)
        .order_by(EmailVerifyCode.id.desc())
    )
    if last:
        elapsed = (datetime.now() - last.created_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail=f"请 {int(RESEND_COOLDOWN_SECONDS - elapsed)} 秒后再重新发送验证码",
            )

    code = str(random.SystemRandom().randint(100000, 999999))
    row = EmailVerifyCode(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=datetime.now() + timedelta(minutes=10),
    )
    db.add(row)
    db.commit()
    try:
        send_email_code(email, code)
    except Exception as exc:
        if os.getenv("DFU_DEV_SHOW_CODE") == "1":
            return {"success": True, "message": f"开发模式验证码：{code}", "dev_code": code}
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=503, detail="验证码邮件发送失败，请稍后重试") from exc
    return {"success": True, "message": f"验证码已发送至 {email}，10 分钟内有效"}


def _consume_code(db: Session, email: str, code: str, purpose: str) -> None:
    row = db.scalar(
        select(EmailVerifyCode)
        .where(EmailVerifyCode.email == email, EmailVerifyCode.purpose == purpose)
        .order_by(EmailVerifyCode.id.desc())
    )
    if not row:
        raise HTTPException(status_code=400, detail="请先获取验证码")
    if row.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    if row.attempts >= MAX_VERIFY_ATTEMPTS:
        raise HTTPException(status_code=400, detail="验证码错误次数过多，请重新获取验证码")
    if row.code != code.strip():
        row.attempts += 1
        db.commit()
        remaining = MAX_VERIFY_ATTEMPTS - row.attempts
        raise HTTPException(status_code=400, detail=f"验证码错误，还剩 {remaining} 次尝试机会")
    db.delete(row)


@app.post("/api/email/register")
async def email_register(req: EmailRegisterRequest, db: Session = Depends(get_db)):
    email = _validate_email_or_400(req.email)
    password = _validate_password_or_400(req.password)
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="该邮箱已被注册，请直接登录")
    _consume_code(db, email, req.code, "register")
    user = User(role="patient", email=email, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    profile = db.scalar(select(PatientProfile).where(PatientProfile.email == email))
    if profile:
        profile.user_id = user.id
    else:
        db.add(
            PatientProfile(
                user_id=user.id,
                patient_code=_patient_code(db),
                email=email,
                created_by=user.id,
            )
        )
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "注册成功", "data": _token_response(user)}


@app.post("/api/email/login")
async def email_login(req: EmailLoginRequest, db: Session = Depends(get_db)):
    email = _validate_email_or_400(req.email)
    user = db.scalar(select(User).where(User.email == email, User.role == "patient"))
    if not user or not user.is_active or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    user.last_login_at = datetime.now()
    db.commit()
    return {"success": True, "message": "登录成功", "data": _token_response(user)}


@app.post("/api/email/reset-password")
async def email_reset_password(req: EmailResetPasswordRequest, db: Session = Depends(get_db)):
    email = _validate_email_or_400(req.email)
    password = _validate_password_or_400(req.new_password)
    user = db.scalar(select(User).where(User.email == email, User.role == "patient"))
    if not user:
        raise HTTPException(status_code=404, detail="该邮箱未注册")
    _consume_code(db, email, req.code, "reset")
    user.password_hash = hash_password(password)
    db.commit()
    return {"success": True, "message": "密码重置成功"}


@app.get("/api/email/me")
async def email_me(user: User = Depends(get_patient_user)):
    return {
        "success": True,
        "data": {"id": user.id, "email": user.email, "role": user.role, "created_at": user.created_at},
    }


# ---------------------------------------------------------------------------
# Patient profile
# ---------------------------------------------------------------------------

def _profile_for_user(db: Session, user: User) -> PatientProfile:
    profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id))
    if not profile:
        profile = PatientProfile(
            user_id=user.id,
            patient_code=_patient_code(db),
            email=user.email,
            created_by=user.id,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _serialize_profile(profile: PatientProfile) -> dict:
    habits = [item.option.code for item in profile.dietary_habits]
    labels = [item.option.label for item in profile.dietary_habits]
    return {
        "id": profile.id,
        "patient_code": profile.patient_code,
        "email": profile.email,
        "phone": profile.phone,
        "name": profile.name,
        "age": profile.age,
        "sex": profile.sex,
        "diabetes_grade": profile.diabetes_grade,
        "residence": profile.residence,
        "dietary_habits": habits,
        "dietary_habit_labels": labels,
        "profile_completed": bool(
            profile.profile_completed
            and profile.name
            and profile.phone
            and profile.age is not None
            and profile.sex
        ),
    }


def _set_profile_phone(db: Session, profile: PatientProfile, value: str) -> str:
    phone = _normalize_phone(value)
    duplicate = db.scalar(
        select(PatientProfile).where(
            PatientProfile.phone == phone,
            PatientProfile.id != profile.id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="该手机号已关联其他患者，请核对后重试")
    profile.phone = phone
    return phone


def _apply_profile(
    db: Session,
    profile: PatientProfile,
    payload: PatientProfileRequest,
    *,
    patient_self_service: bool = False,
) -> None:
    allowed_sexes = {"male", "female"} if patient_self_service else {"male", "female", "other"}
    if payload.sex not in allowed_sexes:
        raise HTTPException(status_code=400, detail="请选择有效的性别")
    if patient_self_service and not (payload.name or "").strip():
        raise HTTPException(status_code=400, detail="请填写姓名")
    if payload.diabetes_grade is not None and payload.diabetes_grade not in {"0", "1", "2", "3", "4", "5", "unknown"}:
        raise HTTPException(status_code=400, detail="请选择有效的糖尿病等级")
    codes = list(dict.fromkeys(payload.dietary_habits))
    options = db.scalars(
        select(DietaryHabitOption).where(
            DietaryHabitOption.code.in_(codes), DietaryHabitOption.is_active.is_(True)
        )
    ).all()
    if len(options) != len(codes):
        raise HTTPException(status_code=400, detail="包含无效的饮食习惯选项")
    _set_profile_phone(db, profile, payload.phone)
    profile.name = (payload.name or "").strip() or None
    profile.age = payload.age
    profile.sex = payload.sex
    if not patient_self_service and payload.diabetes_grade is not None:
        profile.diabetes_grade = payload.diabetes_grade
    profile.residence = (payload.residence or "").strip() or None
    profile.profile_completed = bool(profile.name and profile.phone and profile.age is not None and profile.sex)
    profile.dietary_habits.clear()
    for option in options:
        profile.dietary_habits.append(PatientDietaryHabit(option=option))


@app.get("/api/patient/dietary-options")
async def dietary_options(db: Session = Depends(get_db), _: User = Depends(get_patient_user)):
    rows = db.scalars(
        select(DietaryHabitOption)
        .where(DietaryHabitOption.is_active.is_(True))
        .order_by(DietaryHabitOption.sort_order)
    ).all()
    return {"options": [{"code": row.code, "label": row.label, "description": row.description} for row in rows]}


@app.get("/api/patient/profile")
async def get_patient_profile(db: Session = Depends(get_db), user: User = Depends(get_patient_user)):
    return {"profile": _serialize_profile(_profile_for_user(db, user))}


@app.put("/api/patient/profile")
async def update_patient_profile(
    payload: PatientProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_patient_user),
):
    profile = _profile_for_user(db, user)
    _apply_profile(db, profile, payload, patient_self_service=True)
    db.commit()
    db.refresh(profile)
    return {"success": True, "profile": _serialize_profile(profile)}


# ---------------------------------------------------------------------------
# Doctor authentication and patient management
# ---------------------------------------------------------------------------

@app.post("/api/doctor/register")
async def doctor_register(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    credential = None
    try:
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form = await request.form()
            payload = {key: value for key, value in form.items() if key != "credential"}
            credential = form.get("credential")
        req = DoctorRegisterRequest(**payload)
    except Exception:
        raise HTTPException(status_code=422, detail="请完整填写医生注册资料")

    if credential is None or not getattr(credential, "filename", ""):
        raise HTTPException(status_code=400, detail="请上传执业医师资质证明")
    ext = Path(credential.filename).suffix.lower()
    if ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise HTTPException(status_code=400, detail="资质证明仅支持 PDF、JPG 或 PNG")
    content = await credential.read()
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="资质证明文件大小应在 5MB 以内")

    username = req.username.strip().lower()
    if not username.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="医生账号只能包含字母、数字和下划线")
    password = _validate_password_or_400(req.password)
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=409, detail="该医生账号已存在")

    invitation = None
    for candidate in db.scalars(select(InvitationCode).where(InvitationCode.is_active.is_(True))).all():
        if candidate.expires_at and candidate.expires_at < datetime.now():
            continue
        if candidate.max_uses is not None and candidate.used_count >= candidate.max_uses:
            continue
        if bcrypt.checkpw(req.invitation_code.encode("utf-8"), candidate.code_hash.encode("utf-8")):
            invitation = candidate
            break
    if not invitation:
        raise HTTPException(status_code=403, detail="引荐码无效或已失效")

    stored_path = None
    try:
        user = User(role="doctor", username=username, password_hash=hash_password(password), is_active=True)
        db.add(user)
        db.flush()
        stored_name = f"doctor_{user.id}_{uuid.uuid4().hex}{ext}"
        stored_path = DOCTOR_CREDENTIALS_DIR / stored_name
        stored_path.write_bytes(content)
        db.add(DoctorProfile(
            user_id=user.id,
            real_name=req.real_name.strip(),
            institution=(req.institution or "").strip() or None,
            department=(req.department or "").strip() or None,
            license_number=req.license_number.strip(),
            credential_storage_path=stored_name,
            verification_status="pending",
        ))
        invitation.used_count += 1
        db.commit()
    except Exception:
        db.rollback()
        if stored_path:
            stored_path.unlink(missing_ok=True)
        raise
    return {"success": True, "message": "注册资料已提交，人工审核预计 1 个工作日内完成",
            "verification_status": "pending"}


@app.post("/api/doctor/login")
async def doctor_login(req: DoctorLoginRequest, db: Session = Depends(get_db)):
    username = req.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username, User.role == "doctor"))
    if not user or not user.is_active or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="医生账号或密码错误")
    profile = db.get(DoctorProfile, user.id)
    if not profile or profile.verification_status == "pending":
        raise HTTPException(status_code=403, detail="医生资质正在审核中，审核通过后方可登录")
    if profile.verification_status == "rejected":
        raise HTTPException(status_code=403, detail=profile.verification_note or "医生资质审核未通过")
    user.last_login_at = datetime.now()
    db.commit()
    return {"success": True, "message": "登录成功", "data": _token_response(user)}


@app.get("/api/doctor/me")
async def doctor_me(db: Session = Depends(get_db), user: User = Depends(get_doctor_user)):
    profile = db.get(DoctorProfile, user.id)
    return {
        "success": True,
        "data": {
            "id": user.id,
            "username": user.username,
            "real_name": profile.real_name if profile else user.username,
            "institution": profile.institution if profile else None,
            "department": profile.department if profile else None,
            "license_number": profile.license_number if profile else None,
            "verification_status": profile.verification_status if profile else None,
        },
    }


@app.get("/api/doctor/dietary-options")
async def doctor_dietary_options(db: Session = Depends(get_db), _: User = Depends(get_doctor_user)):
    rows = db.scalars(
        select(DietaryHabitOption)
        .where(DietaryHabitOption.is_active.is_(True))
        .order_by(DietaryHabitOption.sort_order)
    ).all()
    return {"options": [{"code": row.code, "label": row.label, "description": row.description} for row in rows]}


def _mask_name(name: str | None) -> str:
    if not name:
        return "未填写"
    return name[0] + "*" * max(1, len(name) - 1)


def _mask_email(email: str | None) -> str:
    if not email:
        return ""
    local, _, domain = email.partition("@")
    return (local[:2] + "***@" + domain) if domain else "***"


def _ensure_doctor_patient_link(db: Session, doctor_id: int, patient_id: int) -> None:
    link = db.scalar(
        select(DoctorPatientLink).where(
            DoctorPatientLink.doctor_id == doctor_id,
            DoctorPatientLink.patient_profile_id == patient_id,
        )
    )
    if not link:
        db.add(DoctorPatientLink(doctor_id=doctor_id, patient_profile_id=patient_id))


def _doctor_can_access_patient(db: Session, doctor_id: int, patient_id: int) -> bool:
    return bool(
        db.scalar(
            select(DoctorPatientLink.id).where(
                DoctorPatientLink.doctor_id == doctor_id,
                DoctorPatientLink.patient_profile_id == patient_id,
            )
        )
    )


def _validate_draft_options(db: Session, payload: DoctorEncounterDraftRequest) -> list[str]:
    if payload.sex not in {None, "male", "female", "other"}:
        raise HTTPException(status_code=400, detail="性别选项无效")
    if payload.diabetes_grade not in {None, "0", "1", "2", "3", "4", "5", "unknown"}:
        raise HTTPException(status_code=400, detail="糖尿病等级选项无效")
    codes = list(dict.fromkeys(payload.dietary_habits))
    if codes:
        valid_count = db.scalar(
            select(func.count(DietaryHabitOption.id)).where(
                DietaryHabitOption.code.in_(codes), DietaryHabitOption.is_active.is_(True)
            )
        ) or 0
        if valid_count != len(codes):
            raise HTTPException(status_code=400, detail="包含无效的饮食习惯选项")
    return codes


def _apply_encounter_draft(
    db: Session,
    encounter: ClinicalEncounter,
    patient: PatientProfile,
    payload: DoctorEncounterDraftRequest,
    doctor_id: int,
) -> None:
    codes = _validate_draft_options(db, payload)
    phone = _set_profile_phone(db, patient, payload.phone) if payload.phone else patient.phone
    encounter.admission_id = _normalize_admission_id(payload.admission_id)
    encounter.phone_snapshot = phone
    encounter.age = payload.age
    encounter.sex = payload.sex
    encounter.diabetes_grade = payload.diabetes_grade
    encounter.name_snapshot = (payload.name or "").strip() or None
    encounter.residence_snapshot = (payload.residence or "").strip() or None
    encounter.dietary_habits_snapshot = codes
    encounter.updated_by_user_id = doctor_id
    encounter.updated_at = datetime.now()

    if payload.name is not None:
        patient.name = payload.name.strip() or None
    if payload.age is not None:
        patient.age = payload.age
    if payload.sex is not None:
        patient.sex = payload.sex if payload.sex in {"male", "female", "other"} else patient.sex
    if payload.diabetes_grade is not None:
        patient.diabetes_grade = payload.diabetes_grade
    if payload.residence is not None:
        patient.residence = payload.residence.strip() or None
    patient.profile_completed = bool(
        patient.phone
        and patient.age is not None
        and patient.sex
        and patient.diabetes_grade is not None
    )
    patient.dietary_habits.clear()
    if codes:
        options = db.scalars(
            select(DietaryHabitOption).where(DietaryHabitOption.code.in_(codes))
        ).all()
        for option in options:
            patient.dietary_habits.append(PatientDietaryHabit(option=option))


def _serialize_encounter(
    encounter: ClinicalEncounter,
    db: Session | None = None,
    include_patient: bool = False,
) -> dict:
    data = {
        "id": encounter.id,
        "encounter_code": encounter.encounter_code,
        "patient_id": encounter.patient_profile_id,
        "admission_id": encounter.admission_id,
        "phone": encounter.phone_snapshot,
        "age": encounter.age,
        "sex": encounter.sex,
        "diabetes_grade": encounter.diabetes_grade,
        "name": encounter.name_snapshot,
        "residence": encounter.residence_snapshot,
        "dietary_habits": encounter.dietary_habits_snapshot or [],
        "status": encounter.status,
        "is_legacy": encounter.is_legacy,
        "created_at": encounter.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": encounter.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "submitted_at": encounter.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if encounter.submitted_at else None,
    }
    if db is not None:
        data["record_count"] = db.scalar(
            select(func.count(AnalysisRecord.id)).where(AnalysisRecord.encounter_id == encounter.id)
        ) or 0
        if include_patient:
            patient = db.get(PatientProfile, encounter.patient_profile_id)
            data["patient"] = _serialize_profile(patient) if patient else None
    return data


def _doctor_summary(db: Session, doctor: User) -> dict:
    profile = db.get(DoctorProfile, doctor.id)
    return {
        "id": doctor.id,
        "username": doctor.username,
        "real_name": profile.real_name if profile else doctor.username,
        "institution": profile.institution if profile else None,
        "department": profile.department if profile else None,
        "license_number": profile.license_number if profile else None,
        "verification_status": profile.verification_status if profile else None,
    }


def _doctor_encounter(db: Session, doctor: User, encounter_id: int) -> ClinicalEncounter:
    encounter = db.get(ClinicalEncounter, encounter_id)
    if not encounter or not _doctor_can_access_patient(db, doctor.id, encounter.patient_profile_id):
        raise HTTPException(status_code=404, detail="住院记录不存在或无权查看")
    return encounter


@app.post("/api/doctor/patients/lookup")
async def doctor_patient_lookup(
    payload: PatientLookupRequest,
    request: Request,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    raw_query = payload.query.strip()
    if not raw_query:
        raise HTTPException(status_code=400, detail="请输入患者手机号")
    phone = _normalize_phone(raw_query)
    profile = db.scalar(select(PatientProfile).where(PatientProfile.phone == phone))
    matched_encounter = None
    if profile:
        _ensure_doctor_patient_link(db, doctor.id, profile.id)
    _audit(
        db,
        request,
        doctor.id,
        "doctor_patient_lookup",
        target_type="patient_profile",
        target_id=profile.id if profile else None,
        details={"found": bool(profile), "lookup_type": "phone"},
    )
    db.commit()
    if not profile:
        return {"found": False, "query": phone}
    return {
        "found": True,
        "patient": _serialize_profile(profile),
        "matched_encounter": _serialize_encounter(matched_encounter, db) if matched_encounter else None,
    }


@app.post("/api/doctor/patients")
async def doctor_create_patient(
    payload: DoctorCreatePatientRequest,
    request: Request,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    admission_id = _normalize_admission_id(payload.admission_id)
    if db.scalar(select(ClinicalEncounter).where(ClinicalEncounter.admission_id == admission_id)):
        raise HTTPException(status_code=409, detail="该住院ID已经存在，请通过老患者登记查询")
    email = _validate_email_or_400(payload.email) if payload.email else None
    if email and db.scalar(select(PatientProfile).where(PatientProfile.email == email)):
        raise HTTPException(status_code=409, detail="该邮箱已有患者档案，请通过老患者登记查询")
    if payload.phone:
        phone = _normalize_phone(payload.phone)
        if db.scalar(select(PatientProfile).where(PatientProfile.phone == phone)):
            raise HTTPException(status_code=409, detail="该手机号已有患者档案，请通过老患者登记查询")
    patient_user = db.scalar(select(User).where(User.email == email, User.role == "patient")) if email else None
    profile = PatientProfile(
        user_id=patient_user.id if patient_user else None,
        patient_code=_patient_code(db),
        email=email,
        created_by=doctor.id,
    )
    db.add(profile)
    db.flush()
    encounter = ClinicalEncounter(
        encounter_code=_encounter_code(db),
        patient_profile_id=profile.id,
        admission_id=admission_id,
        created_by_user_id=doctor.id,
        updated_by_user_id=doctor.id,
    )
    db.add(encounter)
    _apply_encounter_draft(db, encounter, profile, payload, doctor.id)
    _ensure_doctor_patient_link(db, doctor.id, profile.id)
    _audit(db, request, doctor.id, "doctor_patient_create", target_type="patient_profile", target_id=profile.id)
    db.commit()
    db.refresh(encounter)
    return {
        "success": True,
        "patient": _serialize_profile(profile),
        "encounter": _serialize_encounter(encounter, db),
    }


@app.post("/api/doctor/patients/{patient_id}/encounters")
async def doctor_create_encounter(
    patient_id: int,
    payload: DoctorEncounterDraftRequest,
    request: Request,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    patient = db.get(PatientProfile, patient_id)
    if not patient or not _doctor_can_access_patient(db, doctor.id, patient_id):
        raise HTTPException(status_code=404, detail="患者不存在或尚未关联")
    admission_id = _normalize_admission_id(payload.admission_id)
    existing = db.scalar(select(ClinicalEncounter).where(ClinicalEncounter.admission_id == admission_id))
    if existing:
        if existing.patient_profile_id != patient_id:
            raise HTTPException(status_code=409, detail="该住院ID已归属于其他患者")
        return {
            "success": True,
            "resumed": True,
            "patient": _serialize_profile(patient),
            "encounter": _serialize_encounter(existing, db),
        }
    encounter = ClinicalEncounter(
        encounter_code=_encounter_code(db),
        patient_profile_id=patient_id,
        admission_id=admission_id,
        created_by_user_id=doctor.id,
        updated_by_user_id=doctor.id,
    )
    db.add(encounter)
    _apply_encounter_draft(db, encounter, patient, payload, doctor.id)
    db.flush()
    _audit(
        db,
        request,
        doctor.id,
        "doctor_encounter_create",
        target_type="clinical_encounter",
        target_id=encounter.id,
        details={"patient_id": patient_id, "admission_id": admission_id},
    )
    db.commit()
    return {
        "success": True,
        "resumed": False,
        "patient": _serialize_profile(patient),
        "encounter": _serialize_encounter(encounter, db),
    }


@app.put("/api/doctor/encounters/{encounter_id}")
async def doctor_update_encounter(
    encounter_id: int,
    payload: DoctorEncounterDraftRequest,
    request: Request,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    encounter = _doctor_encounter(db, doctor, encounter_id)
    if encounter.status != "draft":
        raise HTTPException(status_code=409, detail="已归档记录不能直接修改")
    admission_id = _normalize_admission_id(payload.admission_id)
    duplicate = db.scalar(
        select(ClinicalEncounter).where(
            ClinicalEncounter.admission_id == admission_id,
            ClinicalEncounter.id != encounter.id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="该住院ID已经存在")
    patient = db.get(PatientProfile, encounter.patient_profile_id)
    _apply_encounter_draft(db, encounter, patient, payload, doctor.id)
    _audit(db, request, doctor.id, "doctor_encounter_update", target_type="clinical_encounter", target_id=encounter.id)
    db.commit()
    return {
        "success": True,
        "patient": _serialize_profile(patient),
        "encounter": _serialize_encounter(encounter, db),
    }


@app.get("/api/doctor/encounters/{encounter_id}")
async def doctor_get_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    encounter = _doctor_encounter(db, doctor, encounter_id)
    latest_record = db.scalar(
        select(AnalysisRecord)
        .where(AnalysisRecord.encounter_id == encounter.id)
        .order_by(AnalysisRecord.id.desc())
    )
    return {
        "encounter": _serialize_encounter(encounter, db, include_patient=True),
        "doctor": _doctor_summary(db, doctor),
        "latest_record": _record_dict(latest_record, detail=True, db=db) if latest_record else None,
        "archive": _archive_payload(db, encounter, doctor) if latest_record else None,
        "videos": [
            _video_dict(item)
            for item in db.scalars(
                select(ClinicalVideo)
                .where(ClinicalVideo.encounter_id == encounter.id)
                .order_by(ClinicalVideo.id)
            ).all()
        ],
    }


@app.get("/api/doctor/patients/{patient_id}/history")
async def doctor_patient_history(
    patient_id: int,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    patient = db.get(PatientProfile, patient_id)
    if not patient or not _doctor_can_access_patient(db, doctor.id, patient_id):
        raise HTTPException(status_code=404, detail="患者不存在或无权查看")
    encounters = db.scalars(
        select(ClinicalEncounter)
        .where(ClinicalEncounter.patient_profile_id == patient_id)
        .order_by(ClinicalEncounter.id.desc())
    ).all()
    return {
        "patient": _serialize_profile(patient),
        "encounters": [_serialize_encounter(item, db) for item in encounters],
    }


@app.put("/api/doctor/patients/{patient_id}/profile")
async def doctor_update_patient_profile(
    patient_id: int,
    payload: PatientProfileRequest,
    request: Request,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    profile = db.get(PatientProfile, patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail="患者不存在")
    link = db.scalar(
        select(DoctorPatientLink).where(
            DoctorPatientLink.doctor_id == doctor.id,
            DoctorPatientLink.patient_profile_id == profile.id,
        )
    )
    if not link:
        raise HTTPException(status_code=403, detail="请先通过患者手机号完成关联")
    _apply_profile(db, profile, payload)
    _audit(db, request, doctor.id, "doctor_patient_profile_update", target_type="patient_profile", target_id=profile.id)
    db.commit()
    return {"success": True, "patient": _serialize_profile(profile)}


# ---------------------------------------------------------------------------
# Image prediction and records
# ---------------------------------------------------------------------------

async def _read_upload(image: UploadFile) -> tuple[bytes, PILImage.Image, str, str, str]:
    original_name = Path(image.filename or "wound.jpg").name
    ext = Path(original_name).suffix.lower()
    if ext not in IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="请上传 JPG、PNG、BMP 或 WEBP 图片")
    if image.content_type and image.content_type not in IMAGE_MIME_TYPES:
        raise HTTPException(status_code=400, detail="上传内容不是受支持的图片格式")
    content = await image.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="上传图片为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"图片不能超过 {MAX_UPLOAD_BYTES // 1024 // 1024} MB")
    try:
        opened = PILImage.open(io.BytesIO(content))
        opened.load()
        pil_image = ImageOps.exif_transpose(opened).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="无法读取图片内容，请重新选择图片") from exc
    if pil_image.width * pil_image.height > MAX_IMAGE_PIXELS:
        raise HTTPException(status_code=413, detail="图片像素尺寸过大，请压缩后重试")
    detected_format = (opened.format or "").upper()
    format_to_mime = {"JPEG": "image/jpeg", "PNG": "image/png", "BMP": "image/bmp", "WEBP": "image/webp"}
    mime_type = format_to_mime.get(detected_format)
    if not mime_type:
        raise HTTPException(status_code=400, detail="图片真实格式不受支持")
    return content, pil_image, ext, original_name, mime_type


async def _read_video_upload(video: UploadFile) -> tuple[bytes, str, str, str]:
    original_name = Path(video.filename or "video.mp4").name[:255]
    supplied_ext = Path(original_name).suffix.lower()
    if supplied_ext not in {".mp4", ".mov", ".webm"}:
        raise HTTPException(status_code=400, detail="视频仅支持 MP4、MOV 或 WebM 格式")
    content = await video.read(MAX_VIDEO_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="不能上传空视频")
    if len(content) > MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail=f"单个视频不能超过 {MAX_VIDEO_BYTES // 1024 // 1024} MB")
    if len(content) >= 12 and content[4:8] == b"ftyp":
        ext = ".mov" if supplied_ext == ".mov" else ".mp4"
        mime_type = "video/quicktime" if ext == ".mov" else "video/mp4"
    elif content.startswith(b"\x1a\x45\xdf\xa3"):
        ext, mime_type = ".webm", "video/webm"
    else:
        raise HTTPException(status_code=400, detail="视频内容格式无效")
    return content, ext, original_name, mime_type


def _video_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        duration = float(json.loads(result.stdout)["format"]["duration"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="无法验证视频时长或视频文件已损坏") from exc
    if duration <= 0:
        raise HTTPException(status_code=400, detail="视频时长无效")
    if duration > MAX_VIDEO_SECONDS + 0.25:
        raise HTTPException(status_code=413, detail=f"视频时长不能超过 {MAX_VIDEO_SECONDS} 秒")
    return round(duration, 2)


def run_model_prediction(pil_image: PILImage.Image) -> dict:
    """Isolated model boundary so non-GPU API tests can inject a deterministic result."""
    from model_v2 import predict_from_pil

    return predict_from_pil(pil_image)


def _graded_upload_path(grade: str, media_dir: str, stored_name: str) -> tuple[Path, str]:
    grade_dir = GRADE_STORAGE_DIRS.get(grade)
    if not grade_dir:
        raise ValueError(f"不支持的预测等级：{grade}")
    if media_dir not in {"images", "videos"}:
        raise ValueError(f"不支持的媒体目录：{media_dir}")
    relative_path = Path(grade_dir) / media_dir / stored_name
    return UPLOADS_DIR / relative_path, relative_path.as_posix()


def _save_record(
    db: Session,
    content: bytes,
    pil_image: PILImage.Image,
    ext: str,
    original_name: str,
    mime_type: str,
    prediction: dict,
    recommendations: dict,
    report_html: str,
    patient: PatientProfile,
    performer: User,
    source: str,
    encounter: ClinicalEncounter | None = None,
) -> AnalysisRecord:
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path, storage_path = _graded_upload_path(prediction["grade"], "images", stored_name)
    stored_path.write_bytes(content)
    try:
        image_row = MedicalImage(
            storage_path=storage_path,
            original_filename=original_name,
            mime_type=mime_type,
            file_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            width=pil_image.width,
            height=pil_image.height,
            uploaded_by=performer.id,
        )
        db.add(image_row)
        db.flush()
        record = AnalysisRecord(
            patient_profile_id=patient.id,
            encounter_id=encounter.id if encounter else None,
            performed_by_user_id=performer.id,
            source=source,
            image_id=image_row.id,
            image_name=original_name,
            grade=prediction["grade"],
            grade_index=prediction["grade_index"],
            confidence=prediction["confidence"],
            probabilities=prediction["probabilities"],
            is_borderline=prediction["is_borderline"],
            secondary_grade=prediction.get("secondary_grade"),
            secondary_confidence=prediction.get("secondary_confidence"),
            medical=recommendations["medical"],
            lifestyle=recommendations["lifestyle"],
            report_html=report_html,
            model_version=prediction.get("model_version", "unknown"),
        )
        db.add(record)
        db.flush()
        return record
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise


def _save_multi_record(
    db: Session,
    images: list[dict],
    selected_role: str,
    prediction: dict,
    recommendations: dict,
    report_html: str,
    patient: PatientProfile,
    performer: User,
    source: str,
    encounter: ClinicalEncounter | None = None,
) -> AnalysisRecord:
    stored_paths: list[Path] = []
    try:
        image_rows: dict[str, MedicalImage] = {}
        for item in images:
            stored_name = f"{uuid.uuid4()}{item['ext']}"
            stored_path, storage_path = _graded_upload_path(prediction["grade"], "images", stored_name)
            stored_path.write_bytes(item["content"])
            stored_paths.append(stored_path)
            image_row = MedicalImage(
                storage_path=storage_path,
                original_filename=item["original_name"],
                mime_type=item["mime_type"],
                file_size=len(item["content"]),
                sha256=hashlib.sha256(item["content"]).hexdigest(),
                width=item["pil_image"].width,
                height=item["pil_image"].height,
                uploaded_by=performer.id,
            )
            db.add(image_row)
            db.flush()
            image_rows[item["role"]] = image_row

        primary_image = image_rows[selected_role]
        record = AnalysisRecord(
            patient_profile_id=patient.id,
            encounter_id=encounter.id if encounter else None,
            performed_by_user_id=performer.id,
            source=source,
            image_id=primary_image.id,
            image_name=primary_image.original_filename,
            grade=prediction["grade"],
            grade_index=prediction["grade_index"],
            confidence=prediction["confidence"],
            probabilities=prediction["probabilities"],
            is_borderline=prediction["is_borderline"],
            secondary_grade=prediction.get("secondary_grade"),
            secondary_confidence=prediction.get("secondary_confidence"),
            medical=recommendations["medical"],
            lifestyle=recommendations["lifestyle"],
            report_html=report_html,
            model_version=prediction.get("model_version", "unknown"),
        )
        db.add(record)
        db.flush()
        for order, (role, _) in enumerate(CAPTURE_ROLES, start=1):
            db.add(
                AnalysisRecordImage(
                    analysis_record_id=record.id,
                    medical_image_id=image_rows[role].id,
                    image_role=role,
                    sort_order=order,
                )
            )
        db.commit()
        return record
    except Exception:
        db.rollback()
        for stored_path in stored_paths:
            stored_path.unlink(missing_ok=True)
        raise


async def _predict_multi_request(
    uploads: list[tuple[str, str, UploadFile]],
    db: Session,
    patient: PatientProfile | None,
    performer: User | None,
    source: str,
    encounter: ClinicalEncounter | None = None,
) -> dict:
    images: list[dict] = []
    for role, label, upload in uploads:
        content, pil_image, ext, original_name, mime_type = await _read_upload(upload)
        images.append(
            {
                "role": role,
                "label": label,
                "content": content,
                "pil_image": pil_image,
                "ext": ext,
                "original_name": original_name,
                "mime_type": mime_type,
            }
        )

    try:
        closeup_results: list[tuple[str, dict]] = []
        for item in images[3:]:
            prediction = run_model_prediction(item["pil_image"])
            if prediction.get("status") == "rejected":
                return {
                    "status": "rejected",
                    "failed_role": item["role"],
                    "reason": f"{item['label']}未通过图像质量检查："
                    + prediction.get("reason", "请确保创口和创缘清晰可见"),
                }
            closeup_results.append((item["role"], prediction))

        selected_role, prediction = max(
            closeup_results,
            key=lambda pair: (pair[1].get("grade_index", -1), pair[1].get("confidence", 0)),
        )
        recommendations = get_recommendations(prediction)
        report_html = format_report(recommendations)
        record_id = None
        if patient and performer:
            record = _save_multi_record(
                db,
                images,
                selected_role,
                prediction,
                recommendations,
                report_html,
                patient,
                performer,
                source,
                encounter,
            )
            record_id = record.id
        return {
            "status": "ok",
            "prediction": prediction,
            "recommendations": recommendations,
            "report_html": report_html,
            "record_id": record_id,
            "capture_count": len(images),
            "selected_closeup": selected_role,
            "closeup_results": [
                {
                    "role": role,
                    "grade": result["grade"],
                    "confidence": result["confidence"],
                }
                for role, result in closeup_results
            ],
        }
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "多图分析失败，请稍后重试"},
        )


async def _predict_request(
    image: UploadFile,
    db: Session,
    patient: PatientProfile | None,
    performer: User | None,
    source: str,
    encounter: ClinicalEncounter | None = None,
) -> dict:
    content, pil_image, ext, original_name, mime_type = await _read_upload(image)
    try:
        prediction = run_model_prediction(pil_image)
        if prediction.get("status") == "rejected":
            return {
                "status": "rejected",
                "reason": prediction.get("reason", "无法识别该图片，请上传足部溃疡伤口的近景照片"),
                "detail": {
                    "skin_ratio": prediction.get("skin_ratio", 0),
                    "wound_ratio": prediction.get("wound_ratio", 0),
                },
            }
        recommendations = get_recommendations(prediction)
        report_html = format_report(recommendations)
        record_id = None
        if patient and performer:
            record = _save_record(
                db,
                content,
                pil_image,
                ext,
                original_name,
                mime_type,
                prediction,
                recommendations,
                report_html,
                patient,
                performer,
                source,
                encounter,
            )
            db.commit()
            record_id = record.id
        return {
            "status": "ok",
            "prediction": prediction,
            "recommendations": recommendations,
            "report_html": report_html,
            "record_id": record_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": "分析失败，请稍后重试"})


@app.post("/api/predict")
async def api_predict(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_patient_user),
):
    patient = _profile_for_user(db, user)
    if not patient.profile_completed:
        raise HTTPException(status_code=409, detail="请先完成个人信息填写")
    return await _predict_request(image, db, patient, user, "patient")


@app.post("/api/predict-multi")
async def api_predict_multi(
    left_view: UploadFile = File(...),
    right_view: UploadFile = File(...),
    plantar_view: UploadFile = File(...),
    wound_closeup_1: UploadFile = File(...),
    wound_closeup_2: UploadFile = File(...),
    analysis_consent: bool = Form(False),
    research_consent: bool = Form(False),
    followup_consent: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_patient_user),
):
    if not analysis_consent:
        raise HTTPException(status_code=400, detail="请先确认知情同意及非诊断声明")
    patient = _profile_for_user(db, user)
    if not patient.profile_completed:
        raise HTTPException(status_code=409, detail="请先完成个人信息填写")
    uploads = [
        ("left_view", "左侧视角", left_view),
        ("right_view", "右侧视角", right_view),
        ("plantar_view", "足底视角", plantar_view),
        ("wound_closeup_1", "最严重创口特写一", wound_closeup_1),
        ("wound_closeup_2", "最严重创口特写二", wound_closeup_2),
    ]
    result = await _predict_multi_request(uploads, db, patient, user, "patient")
    if isinstance(result, dict) and result.get("status") == "ok" and result.get("record_id"):
        record_id = int(result["record_id"])
        for consent_type, granted in (
            ("analysis", True), ("model_improvement", research_consent), ("followup", followup_consent)
        ):
            db.add(ConsentRecord(patient_profile_id=patient.id, user_id=user.id,
                                 analysis_record_id=record_id, consent_type=consent_type, granted=granted))
        if followup_consent:
            for days in (7, 14):
                db.add(FollowUpPlan(patient_profile_id=patient.id, source_record_id=record_id,
                                    interval_days=days, due_at=datetime.now() + timedelta(days=days)))
        pending = db.scalars(select(FollowUpPlan).where(
            FollowUpPlan.patient_profile_id == patient.id,
            FollowUpPlan.status == "pending",
            FollowUpPlan.source_record_id != record_id,
        ).order_by(FollowUpPlan.due_at)).all()
        if pending:
            pending[0].status = "completed"
            pending[0].completed_record_id = record_id
        db.commit()
    return result


@app.post("/api/doctor/patients/{patient_id}/predict")
async def doctor_predict(
    patient_id: int,
    request: Request,
    image: UploadFile = File(...),
    consent_confirmed: bool = Form(False),
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    patient = db.get(PatientProfile, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    link = db.scalar(
        select(DoctorPatientLink).where(
            DoctorPatientLink.doctor_id == doctor.id,
            DoctorPatientLink.patient_profile_id == patient.id,
        )
    )
    if not link:
        raise HTTPException(status_code=403, detail="请先通过患者邮箱完成关联")
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="请确认已获得患者对本次拍摄和分析的同意")
    if not patient.profile_completed:
        raise HTTPException(status_code=409, detail="请先完成患者个人信息")
    result = await _predict_request(image, db, patient, doctor, "doctor")
    if isinstance(result, dict) and result.get("status") == "ok":
        _audit(
            db,
            request,
            doctor.id,
            "doctor_prediction_create",
            target_type="patient_profile",
            target_id=patient.id,
            details={"consent_confirmed": True},
        )
        db.commit()
    return result


@app.post("/api/doctor/patients/{patient_id}/predict-multi")
async def doctor_predict_multi(
    patient_id: int,
    request: Request,
    left_view: UploadFile = File(...),
    right_view: UploadFile = File(...),
    plantar_view: UploadFile = File(...),
    wound_closeup_1: UploadFile = File(...),
    wound_closeup_2: UploadFile = File(...),
    consent_confirmed: bool = Form(False),
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    patient = db.get(PatientProfile, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    link = db.scalar(
        select(DoctorPatientLink).where(
            DoctorPatientLink.doctor_id == doctor.id,
            DoctorPatientLink.patient_profile_id == patient.id,
        )
    )
    if not link:
        raise HTTPException(status_code=403, detail="请先通过患者邮箱完成关联")
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="请确认已获得患者对本次拍摄和分析的同意")
    if not patient.profile_completed:
        raise HTTPException(status_code=409, detail="请先完成患者个人信息")
    uploads = [
        ("left_view", "左侧视角", left_view),
        ("right_view", "右侧视角", right_view),
        ("plantar_view", "足底视角", plantar_view),
        ("wound_closeup_1", "最严重创口特写一", wound_closeup_1),
        ("wound_closeup_2", "最严重创口特写二", wound_closeup_2),
    ]
    result = await _predict_multi_request(uploads, db, patient, doctor, "doctor")
    if isinstance(result, dict) and result.get("status") == "ok":
        _audit(
            db,
            request,
            doctor.id,
            "doctor_multi_image_prediction_create",
            target_type="patient_profile",
            target_id=patient.id,
            details={"consent_confirmed": True, "capture_count": 5},
        )
        db.commit()
    return result


@app.post("/api/doctor/encounters/{encounter_id}/predict-multi")
async def doctor_encounter_predict_multi(
    encounter_id: int,
    request: Request,
    left_view: UploadFile = File(...),
    right_view: UploadFile = File(...),
    plantar_view: UploadFile = File(...),
    wound_closeup_1: UploadFile = File(...),
    wound_closeup_2: UploadFile = File(...),
    consent_confirmed: bool = Form(False),
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    encounter = _doctor_encounter(db, doctor, encounter_id)
    if encounter.status != "draft":
        raise HTTPException(status_code=409, detail="该住院记录已经归档，不能继续上传")
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="请确认已获得患者对本次拍摄和分析的同意")
    existing_record = db.scalar(
        select(AnalysisRecord.id).where(AnalysisRecord.encounter_id == encounter.id)
    )
    if existing_record:
        raise HTTPException(status_code=409, detail="该草稿已有分析结果，请进入最终核对并提交")
    patient = db.get(PatientProfile, encounter.patient_profile_id)
    uploads = [
        ("left_view", "左侧视角", left_view),
        ("right_view", "右侧视角", right_view),
        ("plantar_view", "足底视角", plantar_view),
        ("wound_closeup_1", "最严重创口特写一", wound_closeup_1),
        ("wound_closeup_2", "最严重创口特写二", wound_closeup_2),
    ]
    result = await _predict_multi_request(uploads, db, patient, doctor, "doctor", encounter)
    if isinstance(result, dict) and result.get("status") == "ok":
        _audit(
            db,
            request,
            doctor.id,
            "doctor_encounter_images_analyzed",
            target_type="clinical_encounter",
            target_id=encounter.id,
            details={"consent_confirmed": True, "capture_count": 5, "record_id": result.get("record_id")},
        )
        db.commit()
        result["encounter"] = _serialize_encounter(encounter, db)
        result["patient"] = _serialize_profile(patient)
    return result


def _video_dict(video: ClinicalVideo) -> dict:
    return {
        "id": video.id,
        "role": video.video_role,
        "label": VIDEO_ROLES.get(video.video_role, video.video_role),
        "filename": video.original_filename,
        "file_size": video.file_size,
        "duration_seconds": video.duration_seconds,
        "created_at": video.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.post("/api/doctor/encounters/{encounter_id}/videos/{video_role}")
async def doctor_upload_optional_video(
    encounter_id: int,
    video_role: str,
    request: Request,
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    if video_role not in VIDEO_ROLES:
        raise HTTPException(status_code=404, detail="视频位置无效")
    encounter = _doctor_encounter(db, doctor, encounter_id)
    if encounter.status != "draft":
        raise HTTPException(status_code=409, detail="已归档记录不能上传视频")
    latest_record = db.scalar(
        select(AnalysisRecord)
        .where(AnalysisRecord.encounter_id == encounter.id)
        .order_by(AnalysisRecord.id.desc())
    )
    if not latest_record:
        raise HTTPException(status_code=409, detail="请先完成影像分析，再上传对应视频")
    content, ext, original_name, mime_type = await _read_video_upload(video)
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path, storage_path = _graded_upload_path(latest_record.grade, "videos", stored_name)
    stored_path.write_bytes(content)
    try:
        duration = _video_duration(stored_path)
        existing = db.scalar(
            select(ClinicalVideo).where(
                ClinicalVideo.encounter_id == encounter.id,
                ClinicalVideo.video_role == video_role,
            )
        )
        old_path = UPLOADS_DIR / existing.storage_path if existing else None
        if existing:
            existing.storage_path = storage_path
            existing.original_filename = original_name
            existing.mime_type = mime_type
            existing.file_size = len(content)
            existing.sha256 = hashlib.sha256(content).hexdigest()
            existing.duration_seconds = duration
            existing.uploaded_by = doctor.id
            existing.created_at = datetime.now()
            row = existing
        else:
            row = ClinicalVideo(
                encounter_id=encounter.id,
                video_role=video_role,
                storage_path=storage_path,
                original_filename=original_name,
                mime_type=mime_type,
                file_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                duration_seconds=duration,
                uploaded_by=doctor.id,
            )
            db.add(row)
        encounter.updated_by_user_id = doctor.id
        encounter.updated_at = datetime.now()
        db.flush()
        _audit(
            db,
            request,
            doctor.id,
            "doctor_optional_video_upload",
            target_type="clinical_encounter",
            target_id=encounter.id,
            details={"video_role": video_role, "duration_seconds": duration},
        )
        db.commit()
        if old_path and old_path != stored_path:
            old_path.unlink(missing_ok=True)
        return {"success": True, "optional": True, "video": _video_dict(row)}
    except Exception:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise


@app.delete("/api/doctor/encounters/{encounter_id}/videos/{video_role}")
async def doctor_delete_optional_video(
    encounter_id: int,
    video_role: str,
    request: Request,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    encounter = _doctor_encounter(db, doctor, encounter_id)
    if encounter.status != "draft":
        raise HTTPException(status_code=409, detail="已归档记录不能删除视频")
    row = db.scalar(
        select(ClinicalVideo).where(
            ClinicalVideo.encounter_id == encounter.id,
            ClinicalVideo.video_role == video_role,
        )
    )
    if not row:
        return {"success": True, "deleted": False}
    path = UPLOADS_DIR / row.storage_path
    db.delete(row)
    _audit(db, request, doctor.id, "doctor_optional_video_delete", target_type="clinical_encounter", target_id=encounter.id, details={"video_role": video_role})
    db.commit()
    path.unlink(missing_ok=True)
    return {"success": True, "deleted": True}


def _archive_payload(db: Session, encounter: ClinicalEncounter, doctor: User) -> dict:
    patient = db.get(PatientProfile, encounter.patient_profile_id)
    latest_record = db.scalar(
        select(AnalysisRecord)
        .where(AnalysisRecord.encounter_id == encounter.id)
        .order_by(AnalysisRecord.id.desc())
    )
    photo_count = db.scalar(
        select(func.count(AnalysisRecordImage.id))
        .join(AnalysisRecord, AnalysisRecord.id == AnalysisRecordImage.analysis_record_id)
        .where(AnalysisRecord.encounter_id == encounter.id)
    ) or 0
    video_count = db.scalar(
        select(func.count(ClinicalVideo.id)).where(ClinicalVideo.encounter_id == encounter.id)
    ) or 0
    return {
        "patient_code": patient.patient_code if patient else None,
        "phone": encounter.phone_snapshot or (patient.phone if patient else None),
        "admission_id": encounter.admission_id,
        "encounter_code": encounter.encounter_code,
        "status": encounter.status,
        "submitted_at": encounter.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if encounter.submitted_at else None,
        "photo_count": photo_count,
        "video_count": video_count,
        "grade": latest_record.grade if latest_record else None,
        "doctor": _doctor_summary(db, doctor),
    }


@app.post("/api/doctor/encounters/{encounter_id}/submit")
async def doctor_submit_encounter(
    encounter_id: int,
    request: Request,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    encounter = _doctor_encounter(db, doctor, encounter_id)
    if encounter.status == "submitted":
        return {"success": True, "already_submitted": True, "archive": _archive_payload(db, encounter, doctor)}
    if encounter.status != "draft":
        raise HTTPException(status_code=409, detail="当前记录状态不能提交")
    missing = []
    if not encounter.admission_id:
        missing.append("住院ID")
    if not encounter.phone_snapshot:
        missing.append("手机号")
    if encounter.age is None:
        missing.append("年龄")
    if encounter.sex is None:
        missing.append("性别")
    if encounter.diabetes_grade is None:
        missing.append("糖尿病等级")
    record_count = db.scalar(
        select(func.count(AnalysisRecord.id)).where(AnalysisRecord.encounter_id == encounter.id)
    ) or 0
    if record_count == 0:
        missing.append("五张足部照片及分析结果")
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"message": "请补充必填内容后再提交", "missing_fields": missing},
        )
    encounter.status = "submitted"
    encounter.submitted_by_user_id = doctor.id
    encounter.updated_by_user_id = doctor.id
    encounter.submitted_at = datetime.now()
    encounter.updated_at = encounter.submitted_at
    _audit(
        db,
        request,
        doctor.id,
        "doctor_encounter_submit",
        target_type="clinical_encounter",
        target_id=encounter.id,
        details={"patient_id": encounter.patient_profile_id, "admission_id": encounter.admission_id},
    )
    db.commit()
    return {"success": True, "already_submitted": False, "archive": _archive_payload(db, encounter, doctor)}


def _record_dict(
    record: AnalysisRecord, detail: bool = False, db: Session | None = None
) -> dict:
    data = {
        "id": record.id,
        "encounter_id": record.encounter_id,
        "grade": record.grade,
        "grade_index": record.grade_index,
        "confidence": record.confidence,
        "is_borderline": record.is_borderline,
        "secondary_grade": record.secondary_grade,
        "secondary_confidence": record.secondary_confidence,
        "source": record.source,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if detail:
        data.update(
            probabilities=record.probabilities,
            medical=record.medical,
            lifestyle=record.lifestyle,
            report_html=record.report_html,
            image_name=record.image_name,
            model_version=record.model_version,
        )
        if db is not None:
            links = db.scalars(
                select(AnalysisRecordImage)
                .where(AnalysisRecordImage.analysis_record_id == record.id)
                .order_by(AnalysisRecordImage.sort_order)
            ).all()
            image_rows = {
                image.id: image
                for image in db.scalars(
                    select(MedicalImage).where(
                        MedicalImage.id.in_([link.medical_image_id for link in links])
                    )
                ).all()
            } if links else {}
            data["images"] = [
                {
                    "role": link.image_role,
                    "label": dict(CAPTURE_ROLES).get(link.image_role, link.image_role),
                    "filename": image_rows[link.medical_image_id].original_filename,
                }
                for link in links
                if link.medical_image_id in image_rows
            ]
    return data


@app.get("/api/records")
async def get_records(db: Session = Depends(get_db), user: User = Depends(get_patient_user)):
    profile = _profile_for_user(db, user)
    rows = db.scalars(
        select(AnalysisRecord)
        .where(AnalysisRecord.patient_profile_id == profile.id)
        .order_by(AnalysisRecord.id.desc())
        .limit(50)
    ).all()
    return {"records": [_record_dict(row) for row in rows]}


@app.get("/api/records/{record_id}")
async def get_record_detail(
    record_id: int, db: Session = Depends(get_db), user: User = Depends(get_patient_user)
):
    profile = _profile_for_user(db, user)
    record = db.scalar(
        select(AnalysisRecord).where(
            AnalysisRecord.id == record_id,
            AnalysisRecord.patient_profile_id == profile.id,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"record": _record_dict(record, detail=True, db=db)}


@app.delete("/api/records/{record_id}")
async def delete_record(
    record_id: int, db: Session = Depends(get_db), user: User = Depends(get_patient_user)
):
    profile = _profile_for_user(db, user)
    record = db.scalar(
        select(AnalysisRecord).where(
            AnalysisRecord.id == record_id,
            AnalysisRecord.patient_profile_id == profile.id,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    links = db.scalars(
        select(AnalysisRecordImage).where(AnalysisRecordImage.analysis_record_id == record.id)
    ).all()
    image_ids = {link.medical_image_id for link in links}
    image_ids.add(record.image_id)
    image_rows = db.scalars(select(MedicalImage).where(MedicalImage.id.in_(image_ids))).all()
    for link in links:
        db.delete(link)
    db.flush()
    db.delete(record)
    db.flush()
    for image_row in image_rows:
        (UPLOADS_DIR / image_row.storage_path).unlink(missing_ok=True)
        db.delete(image_row)
    db.commit()
    return {"success": True, "message": "记录及图片已删除"}


# ---------------------------------------------------------------------------
# Doctor dashboard (only records created by the current doctor)
# ---------------------------------------------------------------------------

@app.get("/api/doctor/dashboard")
async def doctor_dashboard(db: Session = Depends(get_db), doctor: User = Depends(get_doctor_user)):
    base = AnalysisRecord.performed_by_user_id == doctor.id
    total_records = db.scalar(select(func.count(AnalysisRecord.id)).where(base)) or 0
    total_patients = db.scalar(
        select(func.count(DoctorPatientLink.id)).where(DoctorPatientLink.doctor_id == doctor.id)
    ) or 0
    today = datetime.now().date()
    today_records = db.scalar(
        select(func.count(AnalysisRecord.id)).where(base, func.date(AnalysisRecord.created_at) == today)
    ) or 0
    high_risk = db.scalar(
        select(func.count(AnalysisRecord.id)).where(
            base, AnalysisRecord.grade.in_(["Grade 3", "Grade 4", "Grade 5"])
        )
    ) or 0

    grade_rows = db.execute(
        select(AnalysisRecord.grade, func.count(AnalysisRecord.id))
        .where(base)
        .group_by(AnalysisRecord.grade)
        .order_by(AnalysisRecord.grade)
    ).all()
    trend_rows = db.execute(
        select(func.date(AnalysisRecord.created_at), func.count(AnalysisRecord.id))
        .where(base, AnalysisRecord.created_at >= datetime.now() - timedelta(days=29))
        .group_by(func.date(AnalysisRecord.created_at))
        .order_by(func.date(AnalysisRecord.created_at))
    ).all()
    diet_rows = db.execute(
        select(DietaryHabitOption.label, func.count(func.distinct(PatientDietaryHabit.patient_profile_id)))
        .join(PatientDietaryHabit, PatientDietaryHabit.dietary_habit_option_id == DietaryHabitOption.id)
        .join(
            DoctorPatientLink,
            DoctorPatientLink.patient_profile_id == PatientDietaryHabit.patient_profile_id,
        )
        .where(DoctorPatientLink.doctor_id == doctor.id)
        .group_by(DietaryHabitOption.id, DietaryHabitOption.label, DietaryHabitOption.sort_order)
        .order_by(DietaryHabitOption.sort_order)
    ).all()
    recent = db.scalars(
        select(AnalysisRecord).where(base).order_by(AnalysisRecord.id.desc()).limit(20)
    ).all()
    patient_ids = {record.patient_profile_id for record in recent}
    profiles = {
        profile.id: profile
        for profile in db.scalars(select(PatientProfile).where(PatientProfile.id.in_(patient_ids))).all()
    } if patient_ids else {}
    recent_rows = []
    for record in recent:
        profile = profiles.get(record.patient_profile_id)
        row = _record_dict(record)
        row.update(
            patient_id=record.patient_profile_id,
            patient_name=_mask_name(profile.name if profile else None),
            patient_email=_mask_email(profile.email) if profile else "",
        )
        recent_rows.append(row)
    recent_encounters = db.scalars(
        select(ClinicalEncounter)
        .where(ClinicalEncounter.created_by_user_id == doctor.id)
        .order_by(ClinicalEncounter.id.desc())
        .limit(30)
    ).all()
    return {
        "summary": {
            "patients": total_patients,
            "records": total_records,
            "today_records": today_records,
            "high_risk": high_risk,
        },
        "grade_distribution": [{"grade": grade, "count": count} for grade, count in grade_rows],
        "trend": [{"date": str(day), "count": count} for day, count in trend_rows],
        "dietary_habits": [{"label": label, "count": count} for label, count in diet_rows],
        "recent_records": recent_rows,
        "recent_encounters": [
            _serialize_encounter(item, db, include_patient=True) for item in recent_encounters
        ],
        "doctor": _doctor_summary(db, doctor),
    }


@app.get("/api/doctor/workbench")
async def doctor_workbench(
    query: str = "",
    status: str = "all",
    db: Session = Depends(get_db),
    doctor: User = Depends(get_doctor_user),
):
    statement = (
        select(ClinicalEncounter)
        .join(PatientProfile, PatientProfile.id == ClinicalEncounter.patient_profile_id)
        .join(
            DoctorPatientLink,
            DoctorPatientLink.patient_profile_id == PatientProfile.id,
        )
        .where(DoctorPatientLink.doctor_id == doctor.id)
    )
    normalized = query.strip().upper()
    if normalized:
        phone = re.sub(r"[\s-]", "", query.strip())
        if phone.startswith("+86"):
            phone = phone[3:]
        statement = statement.where(
            or_(
                PatientProfile.patient_code == normalized,
                PatientProfile.phone == phone,
                ClinicalEncounter.admission_id == normalized,
                ClinicalEncounter.encounter_code == normalized,
            )
        )
    if status in {"draft", "submitted", "withdrawn"}:
        statement = statement.where(ClinicalEncounter.status == status)
    encounters = db.scalars(statement.order_by(ClinicalEncounter.id.desc()).limit(100)).unique().all()
    return {
        "items": [_serialize_encounter(item, db, include_patient=True) for item in encounters],
        "query": query,
        "status": status,
    }


@app.get("/api/doctor/records/{record_id}")
async def doctor_record_detail(
    record_id: int, db: Session = Depends(get_db), doctor: User = Depends(get_doctor_user)
):
    record = db.scalar(
        select(AnalysisRecord).where(
            AnalysisRecord.id == record_id,
            AnalysisRecord.performed_by_user_id == doctor.id,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在或无权查看")
    profile = db.get(PatientProfile, record.patient_profile_id)
    encounter = db.get(ClinicalEncounter, record.encounter_id) if record.encounter_id else None
    return {
        "record": _record_dict(record, detail=True, db=db),
        "patient": _serialize_profile(profile) if profile else None,
        "encounter": _serialize_encounter(encounter, db) if encounter else None,
        "doctor": _doctor_summary(db, doctor),
    }


def _authorized_report_context(
    db: Session, user: User, record_id: int
) -> tuple[AnalysisRecord, PatientProfile]:
    record = db.get(AnalysisRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="评估记录不存在")

    if user.role == "patient":
        profile = _profile_for_user(db, user)
        if record.patient_profile_id != profile.id:
            raise HTTPException(status_code=404, detail="评估记录不存在或无权下载")
    elif user.role in {"doctor", "admin"}:
        if record.performed_by_user_id != user.id:
            raise HTTPException(status_code=404, detail="评估记录不存在或无权下载")
        profile = db.get(PatientProfile, record.patient_profile_id)
    else:
        raise HTTPException(status_code=403, detail="当前账号无权下载评估报告")

    if not profile:
        raise HTTPException(status_code=404, detail="患者档案不存在")
    return record, profile



@app.get("/api/patient/followups")
async def patient_followups(db: Session = Depends(get_db), user: User = Depends(get_patient_user)):
    patient = _profile_for_user(db, user)
    plans = db.scalars(select(FollowUpPlan).where(
        FollowUpPlan.patient_profile_id == patient.id
    ).order_by(FollowUpPlan.due_at)).all()
    records = db.scalars(select(AnalysisRecord).where(
        AnalysisRecord.patient_profile_id == patient.id
    ).order_by(AnalysisRecord.created_at)).all()
    return {
        "plans": [{"id": row.id, "interval_days": row.interval_days, "due_at": row.due_at.isoformat(),
                   "status": row.status, "channel": row.channel} for row in plans],
        "timeline": [{"id": row.id, "grade": row.grade, "grade_index": row.grade_index,
                      "confidence": row.confidence, "created_at": row.created_at.isoformat()} for row in records],
    }


@app.get("/api/doctor/patients/{patient_id}/care-timeline")
async def doctor_patient_care_timeline(
    patient_id: int, db: Session = Depends(get_db), doctor: User = Depends(get_doctor_user)
):
    if not _doctor_can_access_patient(db, doctor.id, patient_id):
        raise HTTPException(status_code=404, detail="患者不存在或无权查看")
    records = db.scalars(select(AnalysisRecord).where(
        AnalysisRecord.patient_profile_id == patient_id
    ).order_by(AnalysisRecord.created_at)).all()
    referrals = db.scalars(select(ReferralRecord).where(
        ReferralRecord.patient_profile_id == patient_id,
        ReferralRecord.doctor_id == doctor.id,
    ).order_by(ReferralRecord.created_at.desc())).all()
    return {
        "timeline": [{"id": row.id, "grade": row.grade, "grade_index": row.grade_index,
                      "confidence": row.confidence, "created_at": row.created_at.isoformat()} for row in records],
        "referrals": [{"id": row.id, "target_institution": row.target_institution,
                       "reason": row.reason, "status": row.status,
                       "created_at": row.created_at.isoformat()} for row in referrals],
    }


@app.post("/api/doctor/referrals")
async def create_referral(
    req: ReferralRequest, db: Session = Depends(get_db), doctor: User = Depends(get_doctor_user)
):
    if not _doctor_can_access_patient(db, doctor.id, req.patient_id):
        raise HTTPException(status_code=404, detail="患者不存在或无权操作")
    if req.analysis_record_id:
        record = db.get(AnalysisRecord, req.analysis_record_id)
        if not record or record.patient_profile_id != req.patient_id:
            raise HTTPException(status_code=400, detail="评估记录与患者不匹配")
    row = ReferralRecord(patient_profile_id=req.patient_id,
                         analysis_record_id=req.analysis_record_id, doctor_id=doctor.id,
                         target_institution=req.target_institution.strip(), reason=req.reason.strip(),
                         notes=(req.notes or "").strip() or None)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"success": True, "referral_id": row.id}


@app.post("/api/reports/{record_id}/authorize-download")
async def authorize_assessment_report_download(
    record_id: int,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Issue a short-lived, HttpOnly bridge for native browser downloads."""
    _authorized_report_context(db, user, record_id)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    response = JSONResponse(
        {
            "success": True,
            "download_url": f"api/reports/{record_id}/pdf?native=1",
        }
    )
    response.set_cookie(
        key="dfu_report_download",
        value=authorization[7:],
        max_age=120,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return response


@app.get("/api/reports/{record_id}/pdf")
async def download_assessment_report(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Generate an access-controlled auxiliary assessment report."""
    used_download_cookie = False
    if user is None:
        cookie_token = request.cookies.get("dfu_report_download")
        payload = decode_jwt(cookie_token) if cookie_token else None
        try:
            cookie_user_id = int(payload["sub"]) if payload else None
        except (KeyError, TypeError, ValueError):
            cookie_user_id = None
        cookie_user = db.get(User, cookie_user_id) if cookie_user_id else None
        if cookie_user and cookie_user.is_active:
            user = cookie_user
            used_download_cookie = True
    if user is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    record, profile = _authorized_report_context(db, user, record_id)
    encounter = db.get(ClinicalEncounter, record.encounter_id) if record.encounter_id else None
    performer = db.get(User, record.performed_by_user_id)
    operator = (
        _doctor_summary(db, performer)
        if performer and performer.role in {"doctor", "admin"}
        else None
    )
    prediction = {
        "grade": record.grade,
        "confidence": record.confidence,
        "is_borderline": record.is_borderline,
        "secondary_grade": record.secondary_grade,
        "secondary_confidence": record.secondary_confidence,
    }
    recommendations = get_recommendations(prediction)
    pdf_bytes, filename = build_assessment_report(
        record=_record_dict(record, detail=True, db=db),
        patient=_serialize_profile(profile),
        encounter=_serialize_encounter(encounter, db) if encounter else None,
        operator=operator,
        recommendations=recommendations,
    )
    _audit(
        db,
        request,
        user.id,
        "assessment_report_download",
        target_type="analysis_record",
        target_id=record.id,
        details={
            "patient_id": record.patient_profile_id,
            "source": record.source,
            "delivery": "native" if used_download_cookie else "api",
        },
    )
    db.commit()
    response = StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
    if used_download_cookie:
        response.delete_cookie("dfu_report_download", path="/")
    return response


@app.get("/api/health")
async def health():
    from model_v2 import get_model_info

    return {
        "status": "ok",
        "service": "DFU 糖尿病足溃疡智能分级系统",
        "version": "2.1.0",
        "model": get_model_info(load=False),
    }


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("DFU_PORT", "8003")), reload=False)
