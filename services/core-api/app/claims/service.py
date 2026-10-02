from decimal import Decimal
from uuid import UUID

from app.claims.models import ClaimStatus, ExpenseClaim, ExpenseItem
from app.claims.repository import ExpenseClaimRepository
from app.claims.schemas import ExpenseClaimCreate, ExpenseClaimPatch, ExpenseItemInput
from app.core.errors import ClaimItemsRequired, ClaimNotFound, InvalidClaimTransition


class ExpenseClaimService:
    def __init__(self, repository: ExpenseClaimRepository) -> None:
        self._repository = repository

    async def create(self, payload: ExpenseClaimCreate) -> ExpenseClaim:
        claim = ExpenseClaim(
            employee_id=payload.employee_id,
            manager_id=payload.manager_id,
            business_purpose=payload.business_purpose,
            status=ClaimStatus.DRAFT,
            items=[self._build_item(item) for item in payload.items],
        )
        self._recalculate_total(claim)

        async with self._repository.transaction():
            await self._repository.add(claim)

        return claim

    async def get(self, claim_id: UUID) -> ExpenseClaim:
        claim = await self._repository.get_by_id(claim_id)
        if claim is None:
            raise ClaimNotFound()
        return claim

    async def list(
        self,
        *,
        status: ClaimStatus | None,
        employee_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[ExpenseClaim]:
        return await self._repository.list(
            status=status,
            employee_id=employee_id,
            limit=limit,
            offset=offset,
        )

    async def update(self, claim_id: UUID, payload: ExpenseClaimPatch) -> ExpenseClaim:
        async with self._repository.transaction():
            claim = await self._get_for_change(claim_id)
            self._require_status(claim, ClaimStatus.DRAFT)

            if payload.business_purpose is not None:
                claim.business_purpose = payload.business_purpose

            if payload.items is not None:
                claim.items = [self._build_item(item) for item in payload.items]
                self._recalculate_total(claim)

            await self._repository.flush()

        return claim

    async def submit(self, claim_id: UUID) -> ExpenseClaim:
        async with self._repository.transaction():
            claim = await self._get_for_change(claim_id)
            self._require_status(claim, ClaimStatus.DRAFT)
            if not claim.items:
                raise ClaimItemsRequired()
            claim.status = ClaimStatus.SUBMITTED
            await self._repository.flush()
        return claim

    async def approve(self, claim_id: UUID) -> ExpenseClaim:
        return await self._transition(
            claim_id,
            expected=ClaimStatus.SUBMITTED,
            target=ClaimStatus.APPROVED,
        )

    async def reject(self, claim_id: UUID) -> ExpenseClaim:
        return await self._transition(
            claim_id,
            expected=ClaimStatus.SUBMITTED,
            target=ClaimStatus.REJECTED,
        )

    async def reimburse(self, claim_id: UUID) -> ExpenseClaim:
        return await self._transition(
            claim_id,
            expected=ClaimStatus.APPROVED,
            target=ClaimStatus.REIMBURSED,
        )

    async def _transition(
        self,
        claim_id: UUID,
        *,
        expected: ClaimStatus,
        target: ClaimStatus,
    ) -> ExpenseClaim:
        async with self._repository.transaction():
            claim = await self._get_for_change(claim_id)
            self._require_status(claim, expected)
            claim.status = target
            await self._repository.flush()
        return claim

    async def _get_for_change(self, claim_id: UUID) -> ExpenseClaim:
        claim = await self._repository.get_by_id(claim_id)
        if claim is None:
            raise ClaimNotFound()
        return claim

    @staticmethod
    def _require_status(claim: ExpenseClaim, expected: ClaimStatus) -> None:
        if claim.status != expected:
            raise InvalidClaimTransition(
                f"Claim must be {expected.value} for this operation; current status is "
                f"{claim.status.value}"
            )

    @staticmethod
    def _build_item(payload: ExpenseItemInput) -> ExpenseItem:
        return ExpenseItem(
            category=payload.category,
            description=payload.description,
            amount=payload.amount,
            currency=payload.currency,
            expense_date=payload.expense_date,
        )

    @staticmethod
    def _recalculate_total(claim: ExpenseClaim) -> None:
        claim.total_amount = sum(
            (item.amount for item in claim.items),
            start=Decimal("0.00"),
        )
