from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.claims.models import ClaimStatus, ExpenseClaim


class ExpenseClaimRepository(Protocol):
    def transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def add(self, claim: ExpenseClaim) -> None: ...

    async def get_by_id(self, claim_id: UUID) -> ExpenseClaim | None: ...

    async def list(
        self,
        *,
        status: ClaimStatus | None,
        employee_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[ExpenseClaim]: ...

    async def flush(self) -> None: ...


class SqlAlchemyExpenseClaimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        async with self._session.begin():
            yield

    async def add(self, claim: ExpenseClaim) -> None:
        self._session.add(claim)
        await self._session.flush()

    async def get_by_id(self, claim_id: UUID) -> ExpenseClaim | None:
        statement = (
            select(ExpenseClaim)
            .options(selectinload(ExpenseClaim.items))
            .where(ExpenseClaim.id == claim_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        status: ClaimStatus | None,
        employee_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[ExpenseClaim]:
        statement = (
            select(ExpenseClaim)
            .options(selectinload(ExpenseClaim.items))
            .order_by(ExpenseClaim.created_at.desc(), ExpenseClaim.id)
            .limit(limit)
            .offset(offset)
        )

        if status is not None:
            statement = statement.where(ExpenseClaim.status == status)

        if employee_id is not None:
            statement = statement.where(ExpenseClaim.employee_id == employee_id)

        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def flush(self) -> None:
        await self._session.flush()
