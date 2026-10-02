# Phase 1 API Scenario Test Harness

This folder contains black-box HTTP scenarios for learners who want to validate the running Core API without configuring Postman.

The scripts create their own test records using random UUIDs. They do not depend on execution order.

## 1. One-time setup

From the repository root:

    docker compose up -d postgres

Then:

    cd services/core-api
    uv sync
    uv run alembic upgrade head

## 2. Start the API

In terminal 1:

    cd services/core-api
    uv run uvicorn app.main:app --reload

## 3. Run every API scenario

In terminal 2:

    cd services/core-api
    uv run python scripts/api_tests/run_all.py

A successful run ends with:

    TOTAL: <n> passed, 0 failed

Any failed case returns a non-zero process exit code.

## 4. Run one suite only

Smoke/OpenAPI:

    uv run python scripts/api_tests/test_smoke.py

Full happy path:

    uv run python scripts/api_tests/test_happy_path.py

Business rules:

    uv run python scripts/api_tests/test_business_rules.py

Request validation:

    uv run python scripts/api_tests/test_validation.py

State machine:

    uv run python scripts/api_tests/test_state_machine.py

404/error contracts:

    uv run python scripts/api_tests/test_not_found.py

Filtering and pagination:

    uv run python scripts/api_tests/test_filter_pagination.py

Cross-request persistence:

    uv run python scripts/api_tests/test_persistence.py

## 5. Custom API URL

Either pass the URL:

    uv run python scripts/api_tests/run_all.py --base-url http://127.0.0.1:9000

or set:

    EXPENSEFLOW_API_URL=http://127.0.0.1:9000

## 6. Verbose request output

    uv run python scripts/api_tests/run_all.py --verbose

This prints every HTTP method and path as the harness runs.

## What is covered

The black-box harness covers API-observable behavior:

- Swagger/OpenAPI surface
- create/read/update lifecycle
- server-calculated totals
- currency normalization
- empty-claim submission rule
- request validation
- valid and invalid state transitions
- terminal-state immutability
- stable 404/error contracts
- status filtering
- employee filtering
- combined filtering
- pagination
- cross-request persistence

## What intentionally stays in pytest

A public API must not expose a debug endpoint that deliberately crashes a transaction.

Therefore low-level behaviors such as:

- transaction rollback after an internal failure
- repository SQL behavior

remain in the PostgreSQL integration tests under `tests/`.

CI runs both layers:

    black-box HTTP scenarios
        +
    pytest unit/integration tests
