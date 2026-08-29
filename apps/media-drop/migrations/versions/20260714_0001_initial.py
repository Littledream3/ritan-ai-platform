"""Initial anonymous media drop schema.

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("upload_token_hash", sa.String(length=64), nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("total_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batches_ip_created", "upload_batches", ["source_ip", "created_at"], unique=False)
    op.create_index("ix_batches_status_activity", "upload_batches", ["status", "last_activity_at"], unique=False)
    op.create_table(
        "media_files",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("upload_batch_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["upload_batch_id"], ["upload_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
        sa.UniqueConstraint("upload_batch_id", "sha256", name="uq_media_batch_sha256"),
    )
    op.create_index("ix_media_batch_created", "media_files", ["upload_batch_id", "created_at"], unique=False)
    op.create_index("ix_media_kind_created", "media_files", ["kind", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_media_kind_created", table_name="media_files")
    op.drop_index("ix_media_batch_created", table_name="media_files")
    op.drop_table("media_files")
    op.drop_index("ix_batches_status_activity", table_name="upload_batches")
    op.drop_index("ix_batches_ip_created", table_name="upload_batches")
    op.drop_table("upload_batches")
