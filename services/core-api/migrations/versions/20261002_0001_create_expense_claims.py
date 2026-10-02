"""create expense claims and items

Revision ID: 20261002_0001
Revises:
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261002_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

claim_status_values = ["DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "REIMBURSED"]
expense_category_values = ["TRAVEL", "HOTEL", "MEAL", "TRANSPORT", "OTHER"]

claim_status = postgresql.ENUM(*claim_status_values, name="claim_status", create_type=False)
expense_category = postgresql.ENUM(
    *expense_category_values, name="expense_category", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*claim_status_values, name="claim_status").create(bind, checkfirst=True)
    postgresql.ENUM(*expense_category_values, name="expense_category").create(
        bind, checkfirst=True
    )

    op.create_table(
        "expense_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("manager_id", sa.Uuid(), nullable=False),
        sa.Column("business_purpose", sa.String(length=500), nullable=False),
        sa.Column("status", claim_status, nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expense_claims_employee_id", "expense_claims", ["employee_id"])
    op.create_index("ix_expense_claims_manager_id", "expense_claims", ["manager_id"])
    op.create_index("ix_expense_claims_status", "expense_claims", ["status"])

    op.create_table(
        "expense_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("category", expense_category, nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["expense_claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expense_items_claim_id", "expense_items", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_expense_items_claim_id", table_name="expense_items")
    op.drop_table("expense_items")
    op.drop_index("ix_expense_claims_status", table_name="expense_claims")
    op.drop_index("ix_expense_claims_manager_id", table_name="expense_claims")
    op.drop_index("ix_expense_claims_employee_id", table_name="expense_claims")
    op.drop_table("expense_claims")

    bind = op.get_bind()
    postgresql.ENUM(*expense_category_values, name="expense_category").drop(bind, checkfirst=True)
    postgresql.ENUM(*claim_status_values, name="claim_status").drop(bind, checkfirst=True)
