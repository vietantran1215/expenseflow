from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from copy import deepcopy
from uuid import UUID

from app.claims.models import ClaimStatus, ExpenseClaim


class FakeExpenseClaimRepository:
    def __init__(self) -> None:
        self.claims: dict[UUID, ExpenseClaim] = {}

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        snapshot = deepcopy(self.claims)
        try:
            yield
        except Exception:
            self.claims = snapshot
            raise

    async def add(self, claim: ExpenseClaim) -> None:
        if claim.id is None:
            from uuid import uuid4

            claim.id = uuid4()
        self.claims[claim.id] = claim

    async def get_by_id(self, claim_id: UUID) -> ExpenseClaim | None:
        return self.claims.get(claim_id)

    async def list(
        self,
        *,
        status: ClaimStatus | None,
        employee_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[ExpenseClaim]:
        values = list(self.claims.values())
        if status is not None:
            values = [claim for claim in values if claim.status == status]
        if employee_id is not None:
            values = [claim for claim in values if claim.employee_id == employee_id]
        return values[offset : offset + limit]

    async def flush(self) -> None:
        return None
