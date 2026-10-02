# ExpenseFlow

A learning-first enterprise Expense Reimbursement project that evolves from a small FastAPI Core API into secure RAG, agentic workflows, MCP, and OWASP GenAI hardening.

## Current implementation

Phase 1 lives in `services/core-api`. It implements only the Core Expense Claim API and PostgreSQL persistence described in `specs/01-core-api.md`.

Quick start:

    docker compose up -d postgres
    cd services/core-api
    uv sync
    uv run alembic upgrade head
    uv run uvicorn app.main:app --reload

Open `http://127.0.0.1:8000/docs`.

See `specs/` for architecture, technology stack, client, and phase specifications.
