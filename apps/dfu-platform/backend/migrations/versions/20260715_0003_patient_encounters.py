"""Add stable patient codes and admission encounter workflow.

Revision ID: 20260715_0003
Revises: 20260713_0002
Create Date: 2026-07-15
"""
from datetime import datetime
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_0003"
down_revision: Union[str, None] = "20260713_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patient_profiles", sa.Column("patient_code", sa.String(length=32), nullable=True))
    connection = op.get_bind()
    profiles = connection.execute(sa.text("SELECT id FROM patient_profiles ORDER BY id")).all()
    for (profile_id,) in profiles:
        code = f"RT-P-L{profile_id:06d}-{uuid.uuid4().hex[:4].upper()}"
        connection.execute(
            sa.text("UPDATE patient_profiles SET patient_code=:code WHERE id=:profile_id"),
            {"code": code, "profile_id": profile_id},
        )

    with op.batch_alter_table("patient_profiles") as batch_op:
        batch_op.alter_column("patient_code", existing_type=sa.String(length=32), nullable=False)
        batch_op.alter_column("email", existing_type=sa.String(length=254), nullable=True)
    op.create_index("ix_patient_profiles_patient_code", "patient_profiles", ["patient_code"], unique=True)

    op.create_table(
        "clinical_encounters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("encounter_code", sa.String(length=36), nullable=False),
        sa.Column("patient_profile_id", sa.Integer(), nullable=False),
        sa.Column("admission_id", sa.String(length=64), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=10), nullable=True),
        sa.Column("diabetes_grade", sa.String(length=10), nullable=True),
        sa.Column("name_snapshot", sa.String(length=80), nullable=True),
        sa.Column("residence_snapshot", sa.String(length=200), nullable=True),
        sa.Column("dietary_habits_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_legacy", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("submitted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('draft','submitted','withdrawn')", name="ck_encounters_status"),
        sa.CheckConstraint("sex IS NULL OR sex IN ('male','female','other')", name="ck_encounters_sex"),
        sa.CheckConstraint("age IS NULL OR (age >= 0 AND age <= 120)", name="ck_encounters_age"),
        sa.CheckConstraint(
            "diabetes_grade IS NULL OR diabetes_grade IN ('0','1','2','3','4','5','unknown')",
            name="ck_encounters_diabetes_grade",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_profile_id"], ["patient_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinical_encounters_admission_id", "clinical_encounters", ["admission_id"], unique=True)
    op.create_index("ix_clinical_encounters_encounter_code", "clinical_encounters", ["encounter_code"], unique=True)
    op.create_index("ix_clinical_encounters_patient_profile_id", "clinical_encounters", ["patient_profile_id"])
    op.create_index("ix_clinical_encounters_created_by_user_id", "clinical_encounters", ["created_by_user_id"])
    op.create_index("ix_clinical_encounters_updated_by_user_id", "clinical_encounters", ["updated_by_user_id"])
    op.create_index("ix_clinical_encounters_submitted_by_user_id", "clinical_encounters", ["submitted_by_user_id"])
    op.create_index("ix_encounters_patient_created", "clinical_encounters", ["patient_profile_id", "created_at"])
    op.create_index("ix_encounters_doctor_created", "clinical_encounters", ["created_by_user_id", "created_at"])
    op.create_index("ix_encounters_status_updated", "clinical_encounters", ["status", "updated_at"])

    op.create_table(
        "clinical_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("video_role", sa.String(length=30), nullable=False),
        sa.Column("storage_path", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "video_role IN ('full_foot_video','wound_video')",
            name="ck_clinical_videos_role",
        ),
        sa.ForeignKeyConstraint(["encounter_id"], ["clinical_encounters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("encounter_id", "video_role", name="uq_clinical_video_role"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_clinical_videos_encounter_id", "clinical_videos", ["encounter_id"])
    op.create_index("ix_clinical_videos_sha256", "clinical_videos", ["sha256"])
    op.create_index(
        "ix_clinical_videos_encounter_created",
        "clinical_videos",
        ["encounter_id", "created_at"],
    )

    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.add_column(sa.Column("encounter_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_analysis_records_encounter_id",
            "clinical_encounters",
            ["encounter_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_analysis_records_encounter_id", "analysis_records", ["encounter_id"])

    records = connection.execute(
        sa.text(
            "SELECT id, patient_profile_id, performed_by_user_id, created_at "
            "FROM analysis_records ORDER BY id"
        )
    ).all()
    for record_id, patient_id, doctor_id, created_at in records:
        timestamp = created_at or datetime.now()
        habits_expression = ":habits" if connection.dialect.name == "sqlite" else "CAST(:habits AS JSON)"
        result = connection.execute(
            sa.text(
                "INSERT INTO clinical_encounters "
                "(encounter_code, patient_profile_id, admission_id, age, sex, diabetes_grade, "
                "name_snapshot, residence_snapshot, dietary_habits_snapshot, status, is_legacy, "
                "created_by_user_id, updated_by_user_id, submitted_by_user_id, created_at, updated_at, submitted_at) "
                f"VALUES (:code, :patient_id, NULL, NULL, NULL, NULL, NULL, NULL, {habits_expression}, "
                "'submitted', :legacy, :doctor_id, :doctor_id, :doctor_id, :created_at, :created_at, :created_at) "
                "RETURNING id"
            ),
            {
                "code": f"RT-E-L{record_id:08d}",
                "patient_id": patient_id,
                "habits": "[]",
                "legacy": True,
                "doctor_id": doctor_id,
                "created_at": timestamp,
            },
        )
        encounter_id = result.scalar_one()
        connection.execute(
            sa.text("UPDATE analysis_records SET encounter_id=:encounter_id WHERE id=:record_id"),
            {"encounter_id": encounter_id, "record_id": record_id},
        )


def downgrade() -> None:
    op.drop_index("ix_analysis_records_encounter_id", table_name="analysis_records")
    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.drop_constraint("fk_analysis_records_encounter_id", type_="foreignkey")
        batch_op.drop_column("encounter_id")

    op.drop_table("clinical_videos")
    op.drop_table("clinical_encounters")
    op.drop_index("ix_patient_profiles_patient_code", table_name="patient_profiles")
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE patient_profiles SET email='legacy+' || id || '@invalid.local' "
            "WHERE email IS NULL"
        )
    )
    with op.batch_alter_table("patient_profiles") as batch_op:
        batch_op.alter_column("email", existing_type=sa.String(length=254), nullable=False)
        batch_op.drop_column("patient_code")
