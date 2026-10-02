from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.claims.dependencies import ClaimService
from app.claims.models import ClaimStatus
from app.claims.schemas import ExpenseClaimCreate, ExpenseClaimPatch, ExpenseClaimResponse

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("", response_model=ExpenseClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    payload: ExpenseClaimCreate,
    service: ClaimService,
) -> ExpenseClaimResponse:
    return ExpenseClaimResponse.model_validate(await service.create(payload))


@router.get("/{claim_id}", response_model=ExpenseClaimResponse)
async def get_claim(
    claim_id: UUID,
    service: ClaimService,
) -> ExpenseClaimResponse:
    return ExpenseClaimResponse.model_validate(await service.get(claim_id))


@router.get("", response_model=list[ExpenseClaimResponse])
async def list_claims(
    service: ClaimService,
    status_filter: Annotated[ClaimStatus | None, Query(alias="status")] = None,
    employee_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExpenseClaimResponse]:
    claims = await service.list(
        status=status_filter,
        employee_id=employee_id,
        limit=limit,
        offset=offset,
    )
    return [ExpenseClaimResponse.model_validate(claim) for claim in claims]


@router.patch("/{claim_id}", response_model=ExpenseClaimResponse)
async def update_claim(
    claim_id: UUID,
    payload: ExpenseClaimPatch,
    service: ClaimService,
) -> ExpenseClaimResponse:
    return ExpenseClaimResponse.model_validate(await service.update(claim_id, payload))


@router.post("/{claim_id}/submit", response_model=ExpenseClaimResponse)
async def submit_claim(claim_id: UUID, service: ClaimService) -> ExpenseClaimResponse:
    return ExpenseClaimResponse.model_validate(await service.submit(claim_id))


@router.post("/{claim_id}/approve", response_model=ExpenseClaimResponse)
async def approve_claim(claim_id: UUID, service: ClaimService) -> ExpenseClaimResponse:
    return ExpenseClaimResponse.model_validate(await service.approve(claim_id))


@router.post("/{claim_id}/reject", response_model=ExpenseClaimResponse)
async def reject_claim(claim_id: UUID, service: ClaimService) -> ExpenseClaimResponse:
    return ExpenseClaimResponse.model_validate(await service.reject(claim_id))


@router.post("/{claim_id}/reimburse", response_model=ExpenseClaimResponse)
async def reimburse_claim(claim_id: UUID, service: ClaimService) -> ExpenseClaimResponse:
    return ExpenseClaimResponse.model_validate(await service.reimburse(claim_id))
