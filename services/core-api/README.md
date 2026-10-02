# ExpenseFlow Core API — Phase 1

Small FastAPI service for the Expense Reimbursement domain. Phase 1 intentionally has no authentication, AI, cache, message broker, or frontend.

## Quick start

From the repository root:

    docker compose up -d postgres
    cd services/core-api
    uv sync
    uv run alembic upgrade head
    uv run uvicorn app.main:app --reload

Open `http://127.0.0.1:8000/docs`.

The defaults in `app/core/config.py` match the local Docker Compose database, so copying `.env.example` is optional. Use environment variables when overriding configuration.

## Quality checks

With the PostgreSQL container running:

    uv run ruff check .
    uv run mypy app
    uv run pytest

## Phase 1 API

- `POST /claims`
- `GET /claims/{claim_id}`
- `GET /claims`
- `PATCH /claims/{claim_id}`
- `POST /claims/{claim_id}/submit`
- `POST /claims/{claim_id}/approve`
- `POST /claims/{claim_id}/reject`
- `POST /claims/{claim_id}/reimburse`
