from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.claims.models import ClaimStatus, ExpenseCategory


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ExpenseItemInput(StrictModel):
    category: ExpenseCategory
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    expense_date: date

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ExpenseClaimCreate(StrictModel):
    employee_id: UUID
    manager_id: UUID
    business_purpose: str = Field(min_length=1, max_length=500)
    items: list[ExpenseItemInput] = Field(default_factory=list)


class ExpenseClaimPatch(StrictModel):
    business_purpose: str | None = Field(default=None, min_length=1, max_length=500)
    items: list[ExpenseItemInput] | None = None


class ExpenseItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: ExpenseCategory
    description: str
    amount: Decimal
    currency: str
    expense_date: date


class ExpenseClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    manager_id: UUID
    business_purpose: str
    status: ClaimStatus
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[ExpenseItemResponse]
