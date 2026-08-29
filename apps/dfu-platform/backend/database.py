# -*- coding: utf-8 -*-
"""DFU database models and session management.

Production uses PostgreSQL through ``DATABASE_URL``.  A local SQLite fallback is
kept only so the application and tests can run before PostgreSQL is started.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import bcrypt
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'dfu_v2.db').as_posix()}")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('patient','doctor','admin')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class EmailVerifyCode(Base):
    __tablename__ = "email_verify_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), default="register", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    __table_args__ = (
        CheckConstraint("sex IS NULL OR sex IN ('male','female','other')", name="ck_patient_profiles_sex"),
        CheckConstraint("age IS NULL OR (age >= 0 AND age <= 120)", name="ck_patient_profiles_age"),
        CheckConstraint(
            "diabetes_grade IS NULL OR diabetes_grade IN ('0','1','2','3','4','5','unknown')",
            name="ck_patient_profiles_diabetes_grade",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    patient_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(80))
    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(10))
    diabetes_grade: Mapped[str | None] = mapped_column(String(10))
    residence: Mapped[str | None] = mapped_column(String(200))
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    dietary_habits: Mapped[list["PatientDietaryHabit"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    encounters: Mapped[list["ClinicalEncounter"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class DietaryHabitOption(Base):
    __tablename__ = "dietary_habit_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PatientDietaryHabit(Base):
    __tablename__ = "patient_dietary_habits"

    patient_profile_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    dietary_habit_option_id: Mapped[int] = mapped_column(
        ForeignKey("dietary_habit_options.id", ondelete="CASCADE"), primary_key=True
    )

    patient: Mapped[PatientProfile] = relationship(back_populates="dietary_habits")
    option: Mapped[DietaryHabitOption] = relationship()


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    real_name: Mapped[str] = mapped_column(String(80), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(160))
    department: Mapped[str | None] = mapped_column(String(100))
    license_number: Mapped[str | None] = mapped_column(String(100))
    credential_storage_path: Mapped[str | None] = mapped_column(String(255))
    verification_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    verification_note: Mapped[str | None] = mapped_column(String(500))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    verified_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class InvitationCode(Base):
    __tablename__ = "invitation_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(80), default="doctor invitation", nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="doctor", nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class DoctorPatientLink(Base):
    __tablename__ = "doctor_patient_links"
    __table_args__ = (
        UniqueConstraint("doctor_id", "patient_profile_id", name="uq_doctor_patient_link"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_profile_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="limited", nullable=False)
    authorization_method: Mapped[str] = mapped_column(String(40), default="clinical_entry", nullable=False)
    authorized_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ClinicalEncounter(Base):
    """One admission/collection episode linked to a stable patient profile."""

    __tablename__ = "clinical_encounters"
    __table_args__ = (
        CheckConstraint("status IN ('draft','submitted','withdrawn')", name="ck_encounters_status"),
        CheckConstraint("sex IS NULL OR sex IN ('male','female','other')", name="ck_encounters_sex"),
        CheckConstraint("age IS NULL OR (age >= 0 AND age <= 120)", name="ck_encounters_age"),
        CheckConstraint(
            "diabetes_grade IS NULL OR diabetes_grade IN ('0','1','2','3','4','5','unknown')",
            name="ck_encounters_diabetes_grade",
        ),
        Index("ix_encounters_patient_created", "patient_profile_id", "created_at"),
        Index("ix_encounters_doctor_created", "created_by_user_id", "created_at"),
        Index("ix_encounters_status_updated", "status", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_code: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    patient_profile_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    admission_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    phone_snapshot: Mapped[str | None] = mapped_column(String(20))
    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(10))
    diabetes_grade: Mapped[str | None] = mapped_column(String(10))
    name_snapshot: Mapped[str | None] = mapped_column(String(80))
    residence_snapshot: Mapped[str | None] = mapped_column(String(200))
    dietary_habits_snapshot: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    is_legacy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    submitted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)

    patient: Mapped[PatientProfile] = relationship(back_populates="encounters")


class MedicalImage(Base):
    __tablename__ = "medical_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storage_path: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ClinicalVideo(Base):
    __tablename__ = "clinical_videos"
    __table_args__ = (
        UniqueConstraint("encounter_id", "video_role", name="uq_clinical_video_role"),
        CheckConstraint(
            "video_role IN ('full_foot_video','wound_video')",
            name="ck_clinical_videos_role",
        ),
        Index("ix_clinical_videos_encounter_created", "encounter_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_role: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"
    __table_args__ = (
        Index("ix_analysis_patient_created", "patient_profile_id", "created_at"),
        Index("ix_analysis_grade_created", "grade_index", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_profile_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    encounter_id: Mapped[int | None] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="SET NULL"), index=True
    )
    performed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    image_id: Mapped[int] = mapped_column(ForeignKey("medical_images.id", ondelete="RESTRICT"), nullable=False)
    image_name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)
    grade_index: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    probabilities: Mapped[list] = mapped_column(JSON, nullable=False)
    is_borderline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    secondary_grade: Mapped[str | None] = mapped_column(String(20))
    secondary_confidence: Mapped[float | None] = mapped_column(Float)
    medical: Mapped[list] = mapped_column(JSON, nullable=False)
    lifestyle: Mapped[list] = mapped_column(JSON, nullable=False)
    report_html: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), default="resnet50-v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AnalysisRecordImage(Base):
    __tablename__ = "analysis_record_images"
    __table_args__ = (
        UniqueConstraint("analysis_record_id", "image_role", name="uq_analysis_record_image_role"),
        UniqueConstraint("medical_image_id", name="uq_analysis_record_medical_image"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_record_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medical_image_id: Mapped[int] = mapped_column(
        ForeignKey("medical_images.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    image_role: Mapped[str] = mapped_column(String(40), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_actor_created", "actor_user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    __table_args__ = (Index("ix_consent_patient_created", "patient_profile_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_profile_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_records.id", ondelete="SET NULL"), index=True
    )
    consent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(40), default="dfu-consent-2026-07", nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class LeadSubmission(Base):
    __tablename__ = "lead_submissions"
    __table_args__ = (Index("ix_leads_type_created", "lead_type", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    organization: Mapped[str] = mapped_column(String(160), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))
    contact_name: Mapped[str] = mapped_column(String(80), nullable=False)
    contact_value: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    monthly_volume: Mapped[str | None] = mapped_column(String(80))
    cooperation_type: Mapped[str | None] = mapped_column(String(80))
    message: Mapped[str | None] = mapped_column(Text)
    source_page: Mapped[str] = mapped_column(String(80), default="dfu-test", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    crm_sync_status: Mapped[str] = mapped_column(String(20), default="not_configured", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class PartnerInstitution(Base):
    __tablename__ = "partner_institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str | None] = mapped_column(String(120), index=True)
    department: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(255))
    contact_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class FollowUpPlan(Base):
    __tablename__ = "follow_up_plans"
    __table_args__ = (Index("ix_followup_patient_due", "patient_profile_id", "due_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_profile_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_record_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="in_app", nullable=False)
    completed_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_records.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ReferralRecord(Base):
    __tablename__ = "referral_records"
    __table_args__ = (Index("ix_referral_patient_created", "patient_profile_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_profile_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_records.id", ondelete="SET NULL"), index=True
    )
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_institution: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="recommended", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


DIETARY_OPTIONS = [
    ("balanced", "饮食规律、种类均衡", "食物多样并保持规律进餐"),
    ("refined_carbs", "主食或精制碳水偏多", "精制米面或其他精制主食摄入较多"),
    ("high_salt", "高盐、重口味", "咸菜、腌制品或高钠调味品摄入较多"),
    ("high_fat", "高油、油炸食品较多", "油炸食品或高脂食品摄入较多"),
    ("high_sugar", "甜食或含糖饮料较多", "甜点、糖果或含糖饮料摄入较多"),
    ("low_produce", "蔬菜水果摄入不足", "日常蔬菜水果摄入相对不足"),
    ("processed_food", "外卖或加工食品较多", "外卖、预包装或高度加工食品较多"),
    ("irregular_meals", "三餐不规律、夜宵较多", "进餐时间不规律或经常吃夜宵"),
]


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create development tables and seed lookup values.

    Production deployments should run Alembic first; ``create_all`` remains
    idempotent and makes a fresh test environment easy to start.
    """
    Base.metadata.create_all(bind=engine)
    with SessionLocal.begin() as session:
        existing = {row[0] for row in session.query(DietaryHabitOption.code).all()}
        for order, (code, label, description) in enumerate(DIETARY_OPTIONS, start=1):
            if code not in existing:
                session.add(
                    DietaryHabitOption(
                        code=code,
                        label=label,
                        description=description,
                        sort_order=order,
                    )
                )

        if session.query(InvitationCode).count() == 0:
            seed_code = os.getenv("DFU_INITIAL_DOCTOR_INVITE", "ritanai")
            session.add(
                InvitationCode(
                    code_hash=bcrypt.hashpw(seed_code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                    label="initial doctor invitation",
                    role="doctor",
                )
            )


def migrate_db() -> None:
    """Backward-compatible startup hook; schema changes are managed by Alembic."""
    init_db()
