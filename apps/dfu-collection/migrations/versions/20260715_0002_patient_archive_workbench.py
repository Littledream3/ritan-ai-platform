"""Add stable patient archives and encounter identifiers.

Revision ID: 20260715_0002
Revises: 20260714_0001
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_0002"
down_revision: Union[str, None] = "20260714_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("doctors", sa.Column("institution", sa.String(length=120), nullable=True))
    op.add_column("doctors", sa.Column("department", sa.String(length=80), nullable=True))
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_code", sa.String(length=32), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("name", sa.String(length=50), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=10), nullable=True),
        sa.Column("dietary_habit", sa.String(length=40), nullable=True),
        sa.Column("diabetes_grade", sa.String(length=10), nullable=True),
        sa.Column("residence", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patients_patient_code"), "patients", ["patient_code"], unique=True)
    op.create_index(op.f("ix_patients_phone"), "patients", ["phone"], unique=True)

    op.add_column("collection_sessions", sa.Column("encounter_code", sa.String(length=32), nullable=True))
    op.add_column("collection_sessions", sa.Column("admission_id", sa.String(length=64), nullable=True))
    op.add_column("collection_sessions", sa.Column("patient_id", sa.Integer(), nullable=True))
    op.add_column("collection_sessions", sa.Column("phone_snapshot", sa.String(length=20), nullable=True))
    op.add_column("collection_sessions", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("collection_sessions", sa.Column("residence", sa.String(length=100), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT id, patient_name, sex, dietary_habit, diabetes_grade, created_at FROM collection_sessions ORDER BY created_at, id"
    )).mappings().all()
    for index, row in enumerate(rows, start=1):
        patient_code = f"RT-PLEGACY{index:06d}"
        encounter_code = f"RT-ELEGACY{index:06d}"
        admission_id = f"LEGACY-{index:06d}"
        connection.execute(sa.text(
            "INSERT INTO patients (patient_code, phone, name, age, sex, dietary_habit, diabetes_grade, residence, created_at, updated_at) "
            "VALUES (:code, NULL, :name, NULL, :sex, :diet, :grade, NULL, :created, :created)"
        ), {"code": patient_code, "name": row["patient_name"], "sex": row["sex"], "diet": row["dietary_habit"], "grade": row["diabetes_grade"], "created": row["created_at"]})
        patient_id = connection.execute(
            sa.text("SELECT id FROM patients WHERE patient_code = :code"), {"code": patient_code}
        ).scalar_one()
        connection.execute(sa.text(
            "UPDATE collection_sessions SET patient_id=:patient_id, encounter_code=:encounter_code, admission_id=:admission_id WHERE id=:id"
        ), {"patient_id": patient_id, "encounter_code": encounter_code, "admission_id": admission_id, "id": row["id"]})

    with op.batch_alter_table("collection_sessions") as batch:
        batch.create_foreign_key("fk_collection_patient", "patients", ["patient_id"], ["id"], ondelete="RESTRICT")
        batch.alter_column("encounter_code", existing_type=sa.String(length=32), nullable=False)
        batch.alter_column("admission_id", existing_type=sa.String(length=64), nullable=False)
        batch.alter_column("patient_id", existing_type=sa.Integer(), nullable=False)
    op.create_index(op.f("ix_collection_sessions_encounter_code"), "collection_sessions", ["encounter_code"], unique=True)
    op.create_index(op.f("ix_collection_sessions_admission_id"), "collection_sessions", ["admission_id"], unique=True)
    op.create_index("ix_collection_patient_created", "collection_sessions", ["patient_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_collection_patient_created", table_name="collection_sessions")
    op.drop_index(op.f("ix_collection_sessions_admission_id"), table_name="collection_sessions")
    op.drop_index(op.f("ix_collection_sessions_encounter_code"), table_name="collection_sessions")
    op.drop_constraint("fk_collection_patient", "collection_sessions", type_="foreignkey")
    for column in ("residence", "age", "phone_snapshot", "patient_id", "admission_id", "encounter_code"):
        op.drop_column("collection_sessions", column)
    op.drop_index(op.f("ix_patients_phone"), table_name="patients")
    op.drop_index(op.f("ix_patients_patient_code"), table_name="patients")
    op.drop_table("patients")
    op.drop_column("doctors", "department")
    op.drop_column("doctors", "institution")
