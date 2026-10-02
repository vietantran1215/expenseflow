# ExpenseFlow — Technology Stack Specification

## 1. Purpose

This document defines the default technology choices for ExpenseFlow across all ten phases.

The stack is optimized for:

- modern Python backend engineering
- low infrastructure cost
- clear learning progression
- production-relevant patterns
- AI/RAG/agent development
- reproducibility
- security hardening

Exact package versions must be pinned in the project lockfile.

This document specifies baseline release families and architectural choices rather than promising to stay forever on one patch version.

Baseline date: **2026-10-01**.

If a phase specification conflicts with this document, this document is the default authority unless the phase explicitly records a deliberate technology decision.

## 2. Stack Selection Principles

Choose technologies using this priority:

1. required by the learning objective
2. production relevance
3. simplicity
4. maintainability
5. observability
6. security
7. developer experience
8. cloud portability

Every external dependency creates:

- maintenance cost
- security surface
- operational cost
- upgrade risk
- cognitive load

Do not select a technology merely because it is common in enterprise diagrams.

## 3. Runtime

Use:

    Python 3.13

Rationale:

- modern Python runtime
- strong typing/runtime improvements
- broad compatibility with backend and AI packages
- lower compatibility risk than automatically adopting the newest interpreter immediately

Python 3.14 may be adopted after the complete dependency and CI compatibility matrix passes.

Application correctness must not depend on free-threaded Python behavior.

## 4. Package and Environment Management

Use:

    uv

Responsibilities:

- virtual environment management
- dependency installation
- dependency locking
- command execution
- reproducible CI installation

Source of truth:

    pyproject.toml
    uv.lock

Do not maintain parallel dependency manifests unless a target deployment platform explicitly requires an exported format.

## 5. Web Framework

Use:

    FastAPI 0.142.x baseline

As of 2026-09-30, FastAPI 0.142.2 is the latest published release, and the 0.142 line includes native OpenTelemetry support.

Exact patch releases must be locked.

Use FastAPI features directly:

- APIRouter
- dependency injection
- Pydantic request and response models
- lifespan
- exception handlers
- OpenAPI
- SSE when streaming is introduced

Do not build an internal wrapper framework around FastAPI.

## 6. ASGI Server

Use:

    Uvicorn

Local development:

    fastapi dev

or:

    uvicorn package.module:app --reload

Production uses an ASGI deployment compatible with Uvicorn.

Worker/process count is an environment-specific deployment decision.

Do not assume multiple workers are always required.

## 7. Validation and Settings

Use:

    Pydantic v2
    pydantic-settings

Pydantic is used for:

- request DTOs
- response DTOs
- internal typed contracts
- service configuration
- model-output validation
- MCP tool schemas
- agent routing decisions

Do not use SQLAlchemy ORM classes as public API schemas.

## 8. Relational Database

Use:

    PostgreSQL 18 baseline

Rationale:

- ACID transactions
- relational constraints
- JSON support
- mature production ecosystem
- full-text search
- pgvector extension
- broad observability and backup support

Integration tests that validate PostgreSQL behavior must run against PostgreSQL rather than SQLite.

## 9. ORM and SQL

Use:

    SQLAlchemy 2.0.x

As of 2026-09-15, SQLAlchemy 2.0.54 is a current 2.0 release.

Use modern 2.x style:

- select(...)
- typed declarative mappings
- explicit sessions
- explicit transaction boundaries

Async PostgreSQL access should use:

    asyncpg

or another explicitly approved SQLAlchemy async PostgreSQL driver.

Repository abstractions should remain thin and domain-specific.

## 10. Schema Migration

Use:

    Alembic

Requirements:

- every schema change is represented as a migration
- a clean database can be built entirely from migrations
- migration history is committed
- application startup must not perform uncontrolled schema mutation

## 11. Vector Search

Use:

    pgvector 0.8.x

As of 2026-07-29, pgvector 0.8.6 is a released version and provides PostgreSQL 18 container support.

Use pgvector initially for:

- embedding storage
- cosine similarity
- exact nearest-neighbor search
- HNSW when approximate search becomes useful
- metadata-aware filtering through SQL

Reason:

> Reuse PostgreSQL until retrieval scale or operational requirements justify another datastore.

Do not introduce a separate vector database in Phase 3 without a deliberate experiment objective.

## 12. Lexical Search

Phase 6 default:

    PostgreSQL Full-Text Search

Use this first for lexical and exact-term retrieval.

Optional substitution when justified:

    OpenSearch

OpenSearch is not mandatory for the baseline architecture.

The retrieval abstraction must prevent agent orchestration from depending on a specific search engine.

## 13. Object Storage

Phase 7 development:

    MinIO

Production abstraction:

    S3-compatible object storage

Used for:

- receipt images
- receipt PDFs
- optionally versioned raw policy source files

PostgreSQL stores object keys, metadata, and checksums.

Do not store large binary payloads in ordinary relational rows.

## 14. HTTP Client

Use:

    HTTPX

Used for:

- service-to-service calls
- AI internal Core API tools
- JWKS retrieval where needed
- MCP downstream HTTP integration where applicable

Every outbound client must define:

- timeout
- bounded connection pool
- retry policy
- trace instrumentation

No unbounded default network behavior.

## 15. Authentication Cryptography

Use standards-compatible JWT/JWS libraries.

Required capabilities:

- asymmetric signing
- explicit algorithm allowlist
- issuer validation
- audience validation
- expiration validation
- key identifier support
- JWKS publication

Password hashing:

    Argon2id

Do not implement cryptographic primitives manually.

Refresh tokens must be cryptographically random and stored hashed.

## 16. LLM Provider Integration

Use:

    LangChain model integrations

Primary abstractions:

    ChatOpenAI
    OpenAIEmbeddings

Exact model names are configuration rather than architecture.

Configuration examples:

    LLM_MODEL=<approved-chat-model>
    EMBEDDING_MODEL=<approved-embedding-model>

The AI Service should expose small internal model and embedding interfaces.

Do not scatter direct provider SDK calls throughout business modules.

## 17. RAG Framework Usage

Use LangChain selectively for:

- document loaders
- text splitters
- embedding integration
- retriever integration
- prompt composition where it reduces boilerplate

Do not use high-level chains that hide the mechanics the project intends to teach.

Phase 3 must keep these stages explicit:

    load
      ->
    chunk
      ->
    embed
      ->
    retrieve
      ->
    build context
      ->
    generate
      ->
    cite

## 18. Agent Orchestration

Use:

    LangGraph

Rationale:

- explicit graph/state orchestration
- deterministic and LLM-driven steps can coexist
- bounded workflows
- durable execution capability
- human-in-the-loop support
- suitable observability model

Use explicit StateGraph-style orchestration for the learning implementation.

Do not begin with a free-running autonomous-agent abstraction.

The project remains single-agent unless an explicit future requirement changes this.

## 19. RAG Evaluation

Use:

    Ragas 0.4+ collections-based API

Ragas documentation recommends the collections-based API for new projects.

Core RAG metrics:

- Faithfulness
- Answer Relevancy or Response Relevancy
- Context Precision
- Context Recall

Additional direct retrieval metrics:

- Hit Rate
- Recall@K
- Precision@K
- MRR

Agent metrics may include:

- route accuracy
- Tool Call Accuracy
- Tool Call F1
- Agent Goal Accuracy

Evaluation datasets should be version controlled where practical.

Do not rely exclusively on LLM-as-a-judge metrics.

## 20. MCP

Use:

    Official MCP Python SDK v2

The official Python SDK v2 is the current stable release line.

Deployed transport:

    Streamable HTTP

Local and test transport may use:

- in-process server
- stdio

The SDK supports ASGI integration, so the MCP Server may run behind a standard ASGI host.

Do not build a custom MCP protocol implementation.

## 21. OpenTelemetry

Use:

    OpenTelemetry

Required telemetry:

- traces
- metrics
- structured logs correlated to traces

OpenTelemetry Python currently treats traces and metrics as stable. Log signal maturity should be evaluated before depending on advanced log SDK behavior.

Instrument:

- FastAPI
- HTTPX
- SQLAlchemy where appropriate
- retrieval
- reranking
- model calls
- agent nodes
- MCP calls

## 22. Local Observability Stack

Default local stack:

    OpenTelemetry Collector
    Prometheus
    Grafana
    Jaeger or Tempo

Preferred architecture:

    Application
       |
       v
    OTLP
       |
       v
    OpenTelemetry Collector
       |
       +--> metrics backend
       |
       +--> trace backend

Applications should not be tightly coupled to one commercial observability vendor.

## 23. Structured Logging

Use Python logging or a lightweight structured logging library.

Output format:

    JSON

Required fields where applicable:

- timestamp
- severity
- service
- event
- request_id
- trace_id
- duration_ms
- result

Never log:

- passwords
- password hashes
- access tokens
- refresh tokens
- Authorization headers
- raw secrets

## 24. Testing

Use:

    pytest

Supporting packages when needed:

- pytest-asyncio
- HTTPX ASGI test transport
- Testcontainers
- factory/builder utilities

Testing layers evolve through the project:

- unit tests
- business-rule tests
- API tests
- PostgreSQL integration tests
- contract tests
- RAG evaluation
- agent evaluation
- security regression

Database integration tests should use disposable PostgreSQL infrastructure.

## 25. Linting and Formatting

Use:

    Ruff

Responsibilities:

- linting
- import ordering
- formatting when configured

Do not combine multiple overlapping lint/format tools without a specific need.

## 26. Type Checking

Use:

    mypy

Configuration should become stricter over time.

Focus type safety on:

- service boundaries
- DTOs
- repository contracts
- RAG contracts
- agent state
- MCP schemas
- security context

Do not add both mypy and pyright unless there is a concrete requirement.

## 27. Security Scanning

At minimum introduce:

- dependency vulnerability scanning
- secret scanning
- container scanning when containers are present
- SBOM generation by Phase 9

Replaceable tools may include:

    pip-audit
    Gitleaks
    Trivy
    Syft

The requirement is normative; the exact scanner is replaceable.

## 28. Containerization

Use:

    Docker

Production image requirements:

- non-root runtime user
- minimal runtime image
- no secret inside image layers
- deterministic dependency installation
- pinned base-image strategy
- health/readiness integration where appropriate

Local infrastructure:

    Docker Compose

Docker Compose is sufficient for the baseline learning environment throughout the project.

## 29. CI/CD

Use:

    GitHub Actions

Pipeline evolution:

### Phase 1

    Ruff
    mypy
    unit tests
    PostgreSQL integration tests

### Phase 2

Add:

    authentication/security tests
    secret scanning

### Phase 3

Add:

    ingestion test
    RAG smoke evaluation

### Phase 4

Add:

    evaluation artifact/report
    observability verification

### Phase 5–7

Add:

    agent/retrieval/multimodal regression subsets

### Phase 8

Add:

    MCP contract and integration tests

### Phase 9–10

Add:

    adversarial security regression
    dependency scan
    container scan
    SBOM

Do not run expensive full AI evaluations on every trivial change when cost is unjustified.

Use a small PR suite and a fuller release/nightly suite.

## 30. API Documentation

Use FastAPI-generated:

    OpenAPI
    Swagger UI

API documentation must make visible:

- authentication requirements
- important authorization behavior
- request constraints
- error codes

OpenAPI is not a replacement for architecture documentation.

## 31. Streaming

When streamed AI responses are needed, use:

    Server-Sent Events

FastAPI supports SSE in the current release family.

Use WebSockets only when a real requirement needs bidirectional persistent communication.

Do not introduce WebSockets simply because an LLM streams tokens.

## 32. Caching

Caching is not part of the default stack.

If measurements justify a distributed cache, use:

    Redis

Potential future use cases:

- shared rate-limit counters
- stable metadata caching
- JWKS cache if local in-memory behavior is insufficient

Do not introduce Redis preemptively.

## 33. Background Processing

No task queue is mandatory by default.

If multimodal ingestion becomes too slow for synchronous execution, introduce a background-job boundary.

Possible implementation choices:

- database-backed job state
- managed cloud queue
- Celery/RQ only when their operational cost is justified

Rule:

> Prove synchronous processing is insufficient before adding queue infrastructure.

## 34. Retrieval and Reranking Stack

Phase 6 baseline:

    Retriever Interface
       |
       +--> pgvector dense retrieval
       |
       +--> PostgreSQL FTS lexical retrieval
       |
       v
    Reciprocal Rank Fusion
       |
       v
    Configurable Reranker

Reranking provider/model must be replaceable.

Agent code must depend on a retrieval contract rather than a specific search backend.

## 35. Multimodal Processing

Phase 7 uses the approved model gateway abstraction.

Selected model capability must support:

- image input
- document/PDF input where required
- structured output

Receipt extraction must return Pydantic-validated structured data.

OCR may be introduced only if evaluation shows multimodal extraction needs it.

## 36. Application Security Components

By Phase 9 introduce:

- Secure Context Builder
- LLM Gateway
- structured-output validation
- output sanitization at rendering boundary
- prompt-injection adversarial dataset
- sensitive-data tests
- retrieval-authorization tests
- token/cost/resource budgets
- provenance validation

By Phase 10 introduce:

- trusted agent runtime policy guard
- action-tier classification
- explicit write confirmation
- tool allowlist
- agent budget enforcement
- kill or abort support
- agentic security regression suite

These controls belong in application architecture, not in a single generic guardrail library.

## 37. Version Management Policy

Exact dependency versions belong in:

    uv.lock

Specifications use release families such as:

    FastAPI 0.142.x
    SQLAlchemy 2.0.x
    pgvector 0.8.x
    MCP Python SDK v2
    Ragas 0.4+

Upgrade validation must include:

1. lint and type checks
2. unit tests
3. integration tests
4. relevant RAG evaluations
5. relevant agent evaluations
6. relevant security regressions

Major-version upgrades require explicit review.

## 38. Web Client Stack

The supported browser client is:

    React 19.x
    TypeScript — strict mode
    Rsbuild 2.x
    Rspack 2.x
    React Router 7.x — Data Mode
    Node.js 24 LTS
    pnpm

Rust-based frontend tooling:

- Rsbuild as the application build system
- Rspack as the Rust-based bundler
- built-in SWC path for JSX/TSX transformation
- Biome for formatting and linting
- optional Rust React Compiler path only after compatibility tests pass

Use:

- React Router for browser routing
- TanStack Query for non-trivial server state
- OpenAPI-generated TypeScript contracts
- openapi-fetch or native fetch for typed service calls
- React Hook Form for complex forms
- Zod only where client schema validation adds value
- modern CSS / CSS Modules
- Vitest + React Testing Library
- Playwright for phase-critical end-to-end tests
- SSE/fetch streaming for AI responses when introduced

Do not introduce Redux or another global client-state framework by default.

Do not store access or refresh tokens in localStorage, sessionStorage, or IndexedDB.

The production frontend must compile to static assets and must not require a Node.js application server.

The full client architecture is defined in:

    specs/00-client.md

## 39. Approved Baseline Stack

| Area | Technology |
|---|---|
| Backend language | Python 3.13 |
| Client build runtime | Node.js 24 LTS |
| Client UI runtime | React 19.x |
| Client language | TypeScript, strict mode |
| Client build system | Rsbuild 2.x |
| Client bundler | Rspack 2.x |
| Client routing | React Router 7.x, Data Mode |
| Client server state | TanStack Query |
| Client format/lint | Biome |
| Client package manager | pnpm |
| Client component tests | Vitest + React Testing Library |
| Client E2E tests | Playwright |
| Backend package manager | uv |
| API framework | FastAPI 0.142.x |
| ASGI server | Uvicorn |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Database | PostgreSQL 18 |
| ORM | SQLAlchemy 2.0.x |
| Migration | Alembic |
| PostgreSQL async driver | asyncpg |
| Vector search | pgvector 0.8.x |
| Lexical search | PostgreSQL Full-Text Search initially |
| Object storage | MinIO local / S3-compatible production |
| HTTP client | HTTPX |
| Password hashing | Argon2id |
| LLM integration | LangChain model integrations |
| Agent orchestration | LangGraph |
| RAG evaluation | Ragas 0.4+ |
| MCP | Official MCP Python SDK v2 |
| Production MCP transport | Streamable HTTP |
| Telemetry | OpenTelemetry |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Traces | Jaeger or Tempo |
| Backend tests | pytest |
| Backend lint and format | Ruff |
| Backend type checking | mypy |
| Containers | Docker |
| Local infrastructure | Docker Compose |
| CI/CD | GitHub Actions |

## 40. Phase-to-Stack Matrix

| Phase | New Stack Elements |
|---|---|
| 1 | FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic, pytest; React, TypeScript, Rsbuild/Rspack, React Router, basic typed API client |
| 2 | Argon2id, JWT/JWS, JWKS, HTTPX service integration; frontend session bootstrap and protected routing |
| 3 | LangChain integrations, pgvector, LLM and embeddings; policy Q&A and citation UI |
| 4 | Ragas, OpenTelemetry, Prometheus/Grafana, trace backend; client diagnostics metadata |
| 5 | LangGraph; streaming assistant and tool/evidence activity UI |
| 6 | PostgreSQL FTS or optional OpenSearch, RRF, reranker; retrieval debug UI |
| 7 | MinIO/S3, multimodal model input; receipt upload/preview/analysis UI |
| 8 | MCP Python SDK v2, Streamable HTTP; agent action proposal and confirmation UX |
| 9 | SBOM/security scanners, adversarial LLM security harness; output-rendering hardening |
| 10 | Agent policy guard and agentic security regression harness; confirmation-integrity and termination UX |

A phase must not import future-stack components unless an explicit dependency requires them.

## 41. Technology Rejection Rules

Do not add technology because:

- "enterprise systems use it"
- "we might need scale later"
- "microservices normally have it"
- "AI apps normally use it"
- "it looks good in the diagram"

Add technology only when justified by:

- measured latency
- measured throughput
- security boundary
- consistency requirement
- evaluation result
- operational requirement
- explicit learning objective

## 42. Official References

Periodically validate technology decisions against official documentation:

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/docs/
- pgvector: https://github.com/pgvector/pgvector
- LangChain and LangGraph: https://docs.langchain.com/
- Ragas: https://docs.ragas.io/
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- MCP Python SDK: https://py.sdk.modelcontextprotocol.io/
- OWASP GenAI Security Project: https://genai.owasp.org/

## 43. Definition of Done

The technology stack is correctly applied when:

- each phase uses only the dependencies it needs
- exact versions are reproducibly locked
- service boundaries are not erased by shared libraries
- AI frameworks do not hide the concepts being taught
- production concerns can be added without rewriting the business model
- security-sensitive behavior remains under trusted application control
- infrastructure can be replaced behind explicit interfaces when requirements change

The stack should make the architecture easier to understand, not become the architecture.
