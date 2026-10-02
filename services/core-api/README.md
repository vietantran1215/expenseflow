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

## Learner API scenario tests

No Postman setup is required.

Keep the API running, then from `services/core-api` run every black-box HTTP scenario:

    uv run python scripts/api_tests/run_all.py

Run an individual suite:

    uv run python scripts/api_tests/test_happy_path.py
    uv run python scripts/api_tests/test_validation.py
    uv run python scripts/api_tests/test_state_machine.py
    uv run python scripts/api_tests/test_filter_pagination.py

See `scripts/api_tests/README.md` for the complete list and options.

## Quality checks

With the PostgreSQL container running:

    uv run ruff check .
    uv run mypy app
    uv run pytest

CI additionally starts the real FastAPI process and executes `scripts/api_tests/run_all.py` over HTTP.

## Phase 1 API

- `POST /claims`
- `GET /claims/{claim_id}`
- `GET /claims`
- `PATCH /claims/{claim_id}`
- `POST /claims/{claim_id}/submit`
- `POST /claims/{claim_id}/approve`
- `POST /claims/{claim_id}/reject`
- `POST /claims/{claim_id}/reimburse`
