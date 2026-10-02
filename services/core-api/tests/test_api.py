from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.claims.dependencies import get_claim_service
from app.claims.models import ClaimStatus, ExpenseCategory
from app.claims.schemas import ExpenseClaimResponse, ExpenseItemResponse
from app.core.errors import ClaimNotFound
from app.main import app


def response_claim() -> ExpenseClaimResponse:
    claim_id = uuid4()
    return ExpenseClaimResponse(
        id=claim_id,
        employee_id=uuid4(),
        manager_id=uuid4(),
        business_purpose="Conference",
        status=ClaimStatus.DRAFT,
        total_amount=Decimal("100.00"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        items=[
            ExpenseItemResponse(
                id=uuid4(),
                category=ExpenseCategory.TRAVEL,
                description="Train",
                amount=Decimal("100.00"),
                currency="USD",
                expense_date=date(2026, 10, 1),
            )
        ],
    )


class CreateClaimStub:
    def __init__(self, claim: ExpenseClaimResponse) -> None:
        self.claim = claim

    async def create(self, _payload: object) -> ExpenseClaimResponse:
        return self.claim


class MissingClaimStub:
    async def get(self, _claim_id: UUID) -> ExpenseClaimResponse:
        raise ClaimNotFound()


@pytest.fixture
def claim() -> ExpenseClaimResponse:
    return response_claim()


@pytest.fixture
async def client(claim: ExpenseClaimResponse) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_claim_service] = lambda: CreateClaimStub(claim)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_claim_returns_201(client: AsyncClient, claim: ExpenseClaimResponse) -> None:
    response = await client.post(
        "/claims",
        json={
            "employee_id": str(claim.employee_id),
            "manager_id": str(claim.manager_id),
            "business_purpose": "Conference",
            "items": [
                {
                    "category": "TRAVEL",
                    "description": "Train",
                    "amount": "100.00",
                    "currency": "usd",
                    "expense_date": "2026-10-01",
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_invalid_item_uses_stable_validation_error(
    client: AsyncClient, claim: ExpenseClaimResponse
) -> None:
    response = await client.post(
        "/claims",
        json={
            "employee_id": str(claim.employee_id),
            "manager_id": str(claim.manager_id),
            "business_purpose": "Conference",
            "items": [
                {
                    "category": "TRAVEL",
                    "description": "Train",
                    "amount": 0,
                    "currency": "USD",
                    "expense_date": "2026-10-01",
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_unknown_request_field_is_rejected(
    client: AsyncClient, claim: ExpenseClaimResponse
) -> None:
    response = await client.post(
        "/claims",
        json={
            "employee_id": str(claim.employee_id),
            "manager_id": str(claim.manager_id),
            "business_purpose": "Conference",
            "items": [],
            "total_amount": "999999.99",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_missing_claim_uses_stable_domain_error(claim: ExpenseClaimResponse) -> None:
    app.dependency_overrides[get_claim_service] = MissingClaimStub
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        response = await test_client.get(f"/claims/{uuid4()}")
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "code": "CLAIM_NOT_FOUND",
        "message": "Expense claim was not found",
    }
