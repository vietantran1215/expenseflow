import os
from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.claims.models import ClaimStatus, ExpenseCategory, ExpenseClaim, ExpenseItem
from app.claims.repository import SqlAlchemyExpenseClaimRepository
from app.db.session import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://expenseflow:expenseflow@localhost:5432/expenseflow_test",
)


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


def make_claim(
    *,
    status: ClaimStatus,
    employee_id: UUID | None = None,
) -> ExpenseClaim:
    expense_claim = ExpenseClaim(
        employee_id=employee_id or uuid4(),
        manager_id=uuid4(),
        business_purpose="Repository test",
        status=status,
        total_amount=Decimal("25.00"),
    )
    expense_claim.items = [
        ExpenseItem(
            category=ExpenseCategory.MEAL,
            description="Lunch",
            amount=Decimal("25.00"),
            currency="USD",
            expense_date=date(2026, 10, 1),
        )
    ]
    return expense_claim


@pytest.mark.asyncio
async def test_list_filters_status_and_employee_in_database(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    employee_id = uuid4()
    async with session_factory() as session:
        repository = SqlAlchemyExpenseClaimRepository(session)
        async with repository.transaction():
            await repository.add(make_claim(status=ClaimStatus.DRAFT, employee_id=employee_id))
            await repository.add(
                make_claim(status=ClaimStatus.APPROVED, employee_id=employee_id)
            )
            await repository.add(make_claim(status=ClaimStatus.DRAFT))

        rows = await repository.list(
            status=ClaimStatus.DRAFT,
            employee_id=employee_id,
            limit=20,
            offset=0,
        )

    assert len(rows) == 1
    assert rows[0].employee_id == employee_id
    assert rows[0].status == ClaimStatus.DRAFT


@pytest.mark.asyncio
async def test_transaction_rolls_back_partial_create(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    expense_claim = make_claim(status=ClaimStatus.DRAFT)

    with pytest.raises(RuntimeError):
        async with session_factory() as session:
            repository = SqlAlchemyExpenseClaimRepository(session)
            async with repository.transaction():
                await repository.add(expense_claim)
                raise RuntimeError("simulate failure after flush")

    async with session_factory() as verification_session:
        result = await verification_session.execute(
            select(ExpenseClaim).where(ExpenseClaim.id == expense_claim.id)
        )
        persisted = result.scalar_one_or_none()

    assert persisted is None
