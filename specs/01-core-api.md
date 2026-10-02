# Phase 1 — Core API Service

## 1. Purpose

Build the smallest useful Expense Reimbursement backend that still covers the required FastAPI application engineering and persistence concepts. This phase intentionally contains no authentication, AI, messaging, cache, or distributed-system concerns.

The business domain is only **enterprise expense reimbursement**.

Primary learning outcome:

> Build a maintainable FastAPI service with request validation, layered application code, PostgreSQL persistence, migrations, transaction boundaries, filtering, pagination, and explicit business-state transitions.

## 2. Business Scope

An employee creates an expense claim containing one or more expense items. The claim moves through a deliberately small workflow:

    DRAFT
      |
      v
    SUBMITTED
      |
      +------> REJECTED
      |
      v
    APPROVED
      |
      v
    REIMBURSED

Supported expense categories:

- TRAVEL
- HOTEL
- MEAL
- TRANSPORT
- OTHER

This phase does not model travel booking, payroll, cards, procurement, accounting, HR, or vendor management.

## 3. Actors

Authentication does not exist yet, so actors are conceptual only:

- Employee: creates and edits a draft claim, then submits it.
- Manager: approves or rejects a submitted claim.
- Finance: marks an approved claim as reimbursed.

Temporary identifiers such as employee_id and manager_id may be supplied by the request in this phase. Phase 2 will remove trust in client-supplied identity.

## 4. Domain Model

### ExpenseClaim

Required fields:

- id: UUID
- employee_id: UUID
- manager_id: UUID
- business_purpose: string
- status: DRAFT | SUBMITTED | APPROVED | REJECTED | REIMBURSED
- total_amount: decimal, server-calculated
- created_at: datetime
- updated_at: datetime

### ExpenseItem

Required fields:

- id: UUID
- claim_id: UUID
- category: enum
- description: string
- amount: decimal greater than zero
- currency: ISO-like three-letter code
- expense_date: date

The server must calculate claim.total_amount from its items. Clients must not be able to set the persisted total directly.

## 5. Business Rules

BR-01. A new claim starts as DRAFT.

BR-02. Only DRAFT claims may be edited.

BR-03. A claim must contain at least one item before submission.

BR-04. Every item amount must be greater than zero.

BR-05. total_amount equals the sum of item amounts.

BR-06. Only DRAFT may transition to SUBMITTED.

BR-07. Only SUBMITTED may transition to APPROVED or REJECTED.

BR-08. Only APPROVED may transition to REIMBURSED.

BR-09. REJECTED and REIMBURSED are terminal in this phase.

BR-10. State transitions must be enforced in the service layer, not only in route handlers.

## 6. Required API Surface

The implementation should stay near the minimum surface needed to exercise the concepts.

### Create a claim

POST /claims

Request contains:

- employee_id
- manager_id
- business_purpose
- items

Returns HTTP 201.

### Get one claim

GET /claims/{claim_id}

Returns HTTP 200 or 404.

### List claims

GET /claims

Supported query parameters:

- status
- employee_id
- limit
- offset

The repository must apply filtering and pagination in SQL, not after loading all rows.

### Update draft claim

PATCH /claims/{claim_id}

Only business_purpose and items are mutable.

### Submit

POST /claims/{claim_id}/submit

### Approve

POST /claims/{claim_id}/approve

### Reject

POST /claims/{claim_id}/reject

### Mark reimbursed

POST /claims/{claim_id}/reimburse

Eight endpoints are enough. Do not add CRUD endpoints just because CRUD is easy to generate.

## 7. Architecture

Use a small layered structure:

    HTTP Router
        |
        v
    Service
        |
        v
    Repository
        |
        v
    SQLAlchemy
        |
        v
    PostgreSQL

Expected project shape:

    services/core-api/
    ├── app/
    │   ├── main.py
    │   ├── core/
    │   │   ├── config.py
    │   │   └── errors.py
    │   ├── db/
    │   │   └── session.py
    │   └── claims/
    │       ├── models.py
    │       ├── schemas.py
    │       ├── repository.py
    │       ├── service.py
    │       ├── dependencies.py
    │       └── router.py
    ├── migrations/
    ├── tests/
    ├── pyproject.toml
    └── .env.example

No generic "utils" dumping ground.

## 8. Technical Requirements

### FastAPI

Must demonstrate:

- FastAPI application creation
- APIRouter
- request-body validation
- path parameters
- query parameters
- response models
- status codes
- dependency injection
- exception mapping
- OpenAPI generation

### Pydantic

Separate request schemas from response schemas.

Request schemas must reject invalid categories, non-positive amounts, malformed currency values, and empty required text.

Prefer strict request contracts. Unknown business fields should not silently become persisted state.

### SQLAlchemy

Use SQLAlchemy 2.x style.

The API layer must not issue SQLAlchemy queries directly.

### PostgreSQL

Use PostgreSQL as the primary datastore.

SQLite is not the acceptance environment because transaction and PostgreSQL behavior are part of the phase.

### Alembic

Schema changes must be represented by migrations.

Fresh setup must be reproducible from migrations.

### Session lifecycle

Create one request-scoped database session dependency.

Commit/rollback behavior must be explicit.

### Transactions

Creating a claim and its items must be atomic.

Submitting a claim must update the persisted status transactionally.

### Configuration

Use environment-based configuration for at least:

- DATABASE_URL
- APP_ENV
- LOG_LEVEL

No real secrets committed to Git.

## 9. Error Contract

Use a stable JSON error shape, for example:

~~~json
{
  "code": "INVALID_CLAIM_TRANSITION",
  "message": "Only a draft claim can be submitted"
}
~~~

Minimum errors:

- CLAIM_NOT_FOUND
- INVALID_CLAIM_TRANSITION
- CLAIM_ITEMS_REQUIRED
- INVALID_EXPENSE_ITEM
- VALIDATION_ERROR

Do not expose stack traces or raw SQL errors to API clients.

## 10. Example Service Logic

~~~python
class ExpenseClaimService:
    def __init__(self, repository):
        self.repository = repository

    async def submit(self, claim_id):
        # Load through the repository rather than querying from the route.
        claim = await self.repository.get_by_id(claim_id)

        if claim is None:
            raise ClaimNotFound()

        # Business state is enforced here.
        if claim.status != ClaimStatus.DRAFT:
            raise InvalidClaimTransition()

        if not claim.items:
            raise ClaimItemsRequired()

        claim.status = ClaimStatus.SUBMITTED

        # The repository persists the state inside the current transaction.
        return await self.repository.save(claim)
~~~

## 11. Testing Requirements

Keep testing proportional to Phase 1.

Required:

- service unit tests for state transitions
- API tests for validation and status codes
- repository integration tests against PostgreSQL
- one transaction rollback test

Critical scenarios:

1. Creating a claim calculates total_amount correctly.
2. Submitting an empty claim fails.
3. SUBMITTED cannot be edited.
4. SUBMITTED can be approved.
5. DRAFT cannot be reimbursed.
6. Repository filtering occurs in SQL.
7. A failed create operation does not persist a partial claim.

A large coverage percentage is not the goal. Cover the business risks.

## 12. Acceptance Criteria

AC-01. A developer can start PostgreSQL and the service from documented commands.

AC-02. Alembic can create a clean database schema.

AC-03. All eight required endpoints are documented by OpenAPI.

AC-04. Business transitions follow the state machine exactly.

AC-05. Invalid transitions return a stable 4xx error.

AC-06. Claim creation and items are persisted atomically.

AC-07. total_amount is computed server-side.

AC-08. Listing supports SQL-level status filtering and pagination.

AC-09. Route handlers contain HTTP concerns, not persistence code.

AC-10. Service tests and PostgreSQL integration tests pass.

## 13. Explicitly Out of Scope

Do not implement:

- authentication
- authorization
- password storage
- JWT
- refresh tokens
- audit log
- file uploads
- receipts
- Redis
- background workers
- Kafka or RabbitMQ
- RAG
- LLM calls
- MCP
- Kubernetes
- distributed tracing

## 14. Definition of Done

Phase 1 is done when the repository contains a small Core API that proves the learner understands:

    HTTP contract
        ->
    FastAPI validation
        ->
    service-level business rules
        ->
    repository abstraction
        ->
    SQLAlchemy transaction
        ->
    PostgreSQL persistence

The implementation should be intentionally boring and small. Complexity is introduced only when a later phase has a concrete reason for it.

## Front-end Specification

### Goal

Introduce the smallest usable React client for the Core API without hiding HTTP or business-state behavior from the learner.

### Required routes

    /claims
    /claims/new
    /claims/:claimId

### Required UI

- claim list with status filter and pagination controls
- create-claim form with dynamic expense items
- claim detail page
- edit DRAFT claim
- submit DRAFT claim
- approve/reject SUBMITTED claim
- reimburse APPROVED claim
- visible server-calculated total
- loading, empty, validation, and error states

Because authentication does not exist yet, provide a clearly labeled development-only actor panel for temporary employee_id, manager_id, and conceptual role inputs.

The actor panel must not survive Phase 2.

### State rules

- fetch server state through the typed API client
- do not reproduce the claim transition state machine as an authorization mechanism
- UI may hide impossible actions for usability, but Core API remains authoritative
- refresh/invalidate affected claim queries after mutations

### Front-end acceptance criteria

FE-01. A learner can create and inspect a claim without Postman.

FE-02. A claim with multiple items displays the total returned by the server.

FE-03. Workflow actions display backend validation failures rather than predicting success locally.

FE-04. Refreshing the page preserves business data because state comes from the API/database.

FE-05. No authentication/session code exists yet.

FE-06. The application builds through Rsbuild/Rspack and TypeScript strict mode.

