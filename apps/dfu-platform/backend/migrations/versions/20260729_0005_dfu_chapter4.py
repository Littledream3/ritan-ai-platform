"""DFU chapter 4 consent, leads, follow-up, referrals and doctor review.

Revision ID: 20260729_0005
Revises: 20260715_0004
Create Date: 2026-07-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0005"
down_revision: Union[str, None] = "20260715_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("doctor_profiles") as batch:
        batch.add_column(sa.Column("credential_storage_path", sa.String(255), nullable=True))
        batch.add_column(sa.Column("verification_status", sa.String(20), server_default="approved", nullable=False))
        batch.add_column(sa.Column("verification_note", sa.String(500), nullable=True))
        batch.add_column(sa.Column("verified_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("verified_by_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_doctor_profiles_verified_by", "users", ["verified_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_doctor_profiles_verification_status", "doctor_profiles", ["verification_status"])
    op.alter_column("doctor_profiles", "verification_status", server_default="pending")

    op.create_table("consent_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_profile_id", sa.Integer(), sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_record_id", sa.Integer(), sa.ForeignKey("analysis_records.id", ondelete="SET NULL")),
        sa.Column("consent_type", sa.String(40), nullable=False), sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False, server_default="dfu-consent-2026-07"),
        sa.Column("withdrawn_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_consent_records_patient_profile_id", "consent_records", ["patient_profile_id"])
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index("ix_consent_records_analysis_record_id", "consent_records", ["analysis_record_id"])
    op.create_index("ix_consent_patient_created", "consent_records", ["patient_profile_id", "created_at"])

    op.create_table("lead_submissions",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("lead_type", sa.String(40), nullable=False),
        sa.Column("organization", sa.String(160), nullable=False), sa.Column("department", sa.String(100)),
        sa.Column("contact_name", sa.String(80), nullable=False), sa.Column("contact_value", sa.String(120), nullable=False),
        sa.Column("monthly_volume", sa.String(80)), sa.Column("cooperation_type", sa.String(80)),
        sa.Column("message", sa.Text()), sa.Column("source_page", sa.String(80), nullable=False, server_default="dfu-test"),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("crm_sync_status", sa.String(20), nullable=False, server_default="not_configured"),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_lead_submissions_lead_type", "lead_submissions", ["lead_type"])
    op.create_index("ix_lead_submissions_contact_value", "lead_submissions", ["contact_value"])
    op.create_index("ix_leads_type_created", "lead_submissions", ["lead_type", "created_at"])

    op.create_table("partner_institutions",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(160), nullable=False),
        sa.Column("region", sa.String(120)), sa.Column("department", sa.String(100)), sa.Column("address", sa.String(255)),
        sa.Column("contact_url", sa.String(500)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_partner_institutions_region", "partner_institutions", ["region"])

    op.create_table("follow_up_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_profile_id", sa.Integer(), sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_record_id", sa.Integer(), sa.ForeignKey("analysis_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False), sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("completed_record_id", sa.Integer(), sa.ForeignKey("analysis_records.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_follow_up_plans_patient_profile_id", "follow_up_plans", ["patient_profile_id"])
    op.create_index("ix_follow_up_plans_source_record_id", "follow_up_plans", ["source_record_id"])
    op.create_index("ix_follow_up_plans_due_at", "follow_up_plans", ["due_at"])
    op.create_index("ix_followup_patient_due", "follow_up_plans", ["patient_profile_id", "due_at"])

    op.create_table("referral_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_profile_id", sa.Integer(), sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_record_id", sa.Integer(), sa.ForeignKey("analysis_records.id", ondelete="SET NULL")),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_institution", sa.String(160), nullable=False), sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="recommended"), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_referral_records_patient_profile_id", "referral_records", ["patient_profile_id"])
    op.create_index("ix_referral_records_analysis_record_id", "referral_records", ["analysis_record_id"])
    op.create_index("ix_referral_records_doctor_id", "referral_records", ["doctor_id"])
    op.create_index("ix_referral_patient_created", "referral_records", ["patient_profile_id", "created_at"])


def downgrade() -> None:
    op.drop_table("referral_records")
    op.drop_table("follow_up_plans")
    op.drop_table("partner_institutions")
    op.drop_table("lead_submissions")
    op.drop_table("consent_records")
    op.drop_index("ix_doctor_profiles_verification_status", table_name="doctor_profiles")
    with op.batch_alter_table("doctor_profiles") as batch:
        batch.drop_constraint("fk_doctor_profiles_verified_by", type_="foreignkey")
        batch.drop_column("verified_by_user_id")
        batch.drop_column("verified_at")
        batch.drop_column("verification_note")
        batch.drop_column("verification_status")
        batch.drop_column("credential_storage_path")
