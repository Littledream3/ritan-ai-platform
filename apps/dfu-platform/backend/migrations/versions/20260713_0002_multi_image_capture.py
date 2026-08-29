"""Add five-image capture sets to analysis records.

Revision ID: 20260713_0002
Revises: c50689378714
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260713_0002"
down_revision: Union[str, None] = "c50689378714"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_record_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_record_id", sa.Integer(), nullable=False),
        sa.Column("medical_image_id", sa.Integer(), nullable=False),
        sa.Column("image_role", sa.String(length=40), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_record_id"], ["analysis_records.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["medical_image_id"], ["medical_images.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_record_id", "image_role", name="uq_analysis_record_image_role"
        ),
        sa.UniqueConstraint("medical_image_id", name="uq_analysis_record_medical_image"),
    )
    op.create_index(
        op.f("ix_analysis_record_images_analysis_record_id"),
        "analysis_record_images",
        ["analysis_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_record_images_medical_image_id"),
        "analysis_record_images",
        ["medical_image_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_analysis_record_images_medical_image_id"),
        table_name="analysis_record_images",
    )
    op.drop_index(
        op.f("ix_analysis_record_images_analysis_record_id"),
        table_name="analysis_record_images",
    )
    op.drop_table("analysis_record_images")
