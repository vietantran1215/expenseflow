from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.claims.models import ClaimStatus, ExpenseCategory
from app.claims.schemas import ExpenseClaimCreate, ExpenseClaimPatch, ExpenseItemInput
from app.claims.service import ExpenseClaimService
from app.core.errors import ClaimItemsRequired, InvalidClaimTransition
from tests.fakes import FakeExpenseClaimRepository


def item(amount: str = "12.50") -> ExpenseItemInput:
    return ExpenseItemInput(
        category=ExpenseCategory.MEAL,
        description="Client lunch",
        amount=Decimal(amount),
        currency="usd",
        expense_date=date(2026, 10, 1),
    )


def payload(*items: ExpenseItemInput) -> ExpenseClaimCreate:
    return ExpenseClaimCreate(
        employee_id=uuid4(),
        manager_id=uuid4(),
        business_purpose="Customer workshop",
        items=list(items),
    )


@pytest.mark.asyncio
async def test_create_calculates_total_amount() -> None:
    repository = FakeExpenseClaimRepository()
    service = ExpenseClaimService(repository)

    claim = await service.create(payload(item("10.25"), item("20.50")))

    assert claim.status == ClaimStatus.DRAFT
    assert claim.total_amount == Decimal("30.75")
    assert [expense.currency for expense in claim.items] == ["USD", "USD"]


@pytest.mark.asyncio
async def test_submit_requires_at_least_one_item() -> None:
    service = ExpenseClaimService(FakeExpenseClaimRepository())
    claim = await service.create(payload())

    with pytest.raises(ClaimItemsRequired):
        await service.submit(claim.id)


@pytest.mark.asyncio
async def test_submitted_claim_cannot_be_edited() -> None:
    service = ExpenseClaimService(FakeExpenseClaimRepository())
    claim = await service.create(payload(item()))
    await service.submit(claim.id)

    with pytest.raises(InvalidClaimTransition):
        await service.update(
            claim.id,
            ExpenseClaimPatch(business_purpose="Changed after submit"),
        )


@pytest.mark.asyncio
async def test_submitted_claim_can_be_approved() -> None:
    service = ExpenseClaimService(FakeExpenseClaimRepository())
    claim = await service.create(payload(item()))
    await service.submit(claim.id)

    approved = await service.approve(claim.id)

    assert approved.status == ClaimStatus.APPROVED


@pytest.mark.asyncio
async def test_draft_claim_cannot_be_reimbursed() -> None:
    service = ExpenseClaimService(FakeExpenseClaimRepository())
    claim = await service.create(payload(item()))

    with pytest.raises(InvalidClaimTransition):
        await service.reimburse(claim.id)
