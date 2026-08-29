"""Add patient phone and align patient profile fields.

Revision ID: 20260715_0004
Revises: 20260715_0003
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_0004"
down_revision: Union[str, None] = "20260715_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("patient_profiles") as batch_op:
        batch_op.drop_constraint("ck_patient_profiles_sex", type_="check")
        batch_op.add_column(sa.Column("phone", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("age", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("diabetes_grade", sa.String(length=10), nullable=True))
        batch_op.create_check_constraint(
            "ck_patient_profiles_sex",
            "sex IS NULL OR sex IN ('male','female','other')",
        )
        batch_op.create_check_constraint(
            "ck_patient_profiles_age",
            "age IS NULL OR (age >= 0 AND age <= 120)",
        )
        batch_op.create_check_constraint(
            "ck_patient_profiles_diabetes_grade",
            "diabetes_grade IS NULL OR diabetes_grade IN ('0','1','2','3','4','5','unknown')",
        )
    op.create_index("ix_patient_profiles_phone", "patient_profiles", ["phone"], unique=True)

    with op.batch_alter_table("clinical_encounters") as batch_op:
        batch_op.add_column(sa.Column("phone_snapshot", sa.String(length=20), nullable=True))

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE patient_profiles SET profile_completed=:incomplete "
            "WHERE phone IS NULL OR age IS NULL OR sex IS NULL OR diabetes_grade IS NULL"
        ),
        {"incomplete": False},
    )


def downgrade() -> None:
    with op.batch_alter_table("clinical_encounters") as batch_op:
        batch_op.drop_column("phone_snapshot")

    op.drop_index("ix_patient_profiles_phone", table_name="patient_profiles")
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE patient_profiles SET sex=NULL WHERE sex='other'"))
    with op.batch_alter_table("patient_profiles") as batch_op:
        batch_op.drop_constraint("ck_patient_profiles_diabetes_grade", type_="check")
        batch_op.drop_constraint("ck_patient_profiles_age", type_="check")
        batch_op.drop_constraint("ck_patient_profiles_sex", type_="check")
        batch_op.create_check_constraint("ck_patient_profiles_sex", "sex IN ('male','female')")
        batch_op.drop_column("diabetes_grade")
        batch_op.drop_column("age")
        batch_op.drop_column("phone")
