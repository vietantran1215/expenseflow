from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ClaimStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REIMBURSED = "REIMBURSED"


class ExpenseCategory(StrEnum):
    TRAVEL = "TRAVEL"
    HOTEL = "HOTEL"
    MEAL = "MEAL"
    TRANSPORT = "TRANSPORT"
    OTHER = "OTHER"


class ExpenseClaim(Base):
    __tablename__ = "expense_claims"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(index=True)
    manager_id: Mapped[UUID] = mapped_column(index=True)
    business_purpose: Mapped[str] = mapped_column(String(500))
    status: Mapped[ClaimStatus] = mapped_column(
        SqlEnum(ClaimStatus, name="claim_status"),
        default=ClaimStatus.DRAFT,
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=utc_now,
    )

    items: Mapped[list["ExpenseItem"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ExpenseItem(Base):
    __tablename__ = "expense_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("expense_claims.id", ondelete="CASCADE"),
        index=True,
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        SqlEnum(ExpenseCategory, name="expense_category")
    )
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    expense_date: Mapped[date] = mapped_column(Date)

    claim: Mapped[ExpenseClaim] = relationship(back_populates="items")
