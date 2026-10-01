# ExpenseFlow — Architecture Specification

## 1. Purpose

This document defines the global architecture constraints for ExpenseFlow across all ten phases.

Phase specifications define what changes in each phase. This document defines the service ownership, trust boundaries, data ownership, communication rules, and architectural invariants that must remain coherent while the system evolves.

The business domain remains **Enterprise Expense Reimbursement** from Phase 1 through Phase 10.

If a phase specification conflicts with this document, this document is the default authority unless the phase explicitly records a deliberate architecture change.

## 2. Architecture Goals

ExpenseFlow optimizes for:

1. Clear service ownership.
2. Minimal accidental coupling.
3. Explicit trust boundaries.
4. Secure identity propagation.
5. Independent evolution of Core, Auth, and AI capabilities.
6. Observable request and agent execution paths.
7. Measured rather than speculative complexity.
8. Incremental production hardening.
9. Security controls outside the LLM.
10. Replaceable infrastructure integrations.

Every component must exist because a requirement justifies it.

## 3. Non-Goals

ExpenseFlow is not intended to become:

- a generic ERP
- a generic HR system
- a procurement platform
- a payment platform
- a multi-tenant SaaS framework
- a generic knowledge-management platform
- a generic agent platform
- a multi-agent research system
- a Kubernetes showcase
- an event-driven architecture showcase
- a service-mesh showcase

Do not add infrastructure or distributed-system patterns unless a phase explicitly requires them.

## 4. Business Domain Boundary

ExpenseFlow owns one business capability:

> Employees create expense claims, managers review them, Finance processes approved claims, and AI helps users understand expense policy and prepare compliant claims.

Core business objects:

    ExpenseClaim
    ExpenseItem
    Receipt

Supporting identity objects:

    User
    RefreshSession

Supporting AI knowledge objects:

    PolicyDocument
    PolicyDocumentVersion
    PolicyChunk
    EvaluationCase

Do not create unrelated bounded contexts.

## 5. Final System Context

The final conceptual topology is:

    ┌──────────────────────────────────────────────┐
    │                   Clients                    │
    │ Web / CLI / API Consumer / Agent Consumer   │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Edge / API Entry  │
                 │ optional gateway  │
                 └───────┬───────────┘
                         │
              ┌──────────┼───────────┐
              │          │           │
              ▼          ▼           ▼
        ┌──────────┐ ┌─────────┐ ┌──────────┐
        │ Auth API │ │ Core API│ │  AI API  │
        └────┬─────┘ └────┬────┘ └────┬─────┘
             │            │            │
             ▼            ▼            │
        Auth Database  Core Database   │
                                      │
                          ┌───────────┴───────────┐
                          │                       │
                          ▼                       ▼
                   AI Knowledge Store       Agent Runtime
                   + Vector Search               │
                                                 ▼
                                           MCP Client
                                                 │
                                                 ▼
                                           MCP Server
                                                 │
                                                 ▼
                                             Core API

Cross-cutting concerns:

- OpenTelemetry
- structured logs
- metrics
- audit
- configuration and secrets
- security policy enforcement

This topology is reached gradually. Phase 1 must not implement the final architecture.

## 6. Service Boundary — Core API

The Core API is the business system of record for Expense Reimbursement.

It owns:

- ExpenseClaim
- ExpenseItem
- Receipt metadata
- claim workflow state
- claim ownership
- manager assignment
- reimbursement state
- resource and workflow authorization decisions involving claims

It must not own:

- passwords
- refresh sessions
- embedding vectors
- prompts
- model-provider configuration
- agent state
- MCP protocol behavior

Core business rules stay in Core API even when invoked through AI or MCP.

    Agent
      |
      v
    MCP Server
      |
      v
    Core API
      |
      v
    validate business transition

The MCP Server must never become a second implementation of claim business rules.

## 7. Service Boundary — Auth Service

The Auth Service is the identity and credential authority.

It owns:

- users
- password hashes
- user status
- business role
- manager relationship when represented as identity metadata
- access-token issuance
- signing keys
- JWKS
- refresh sessions
- token rotation and revocation
- authentication audit events

It must not own:

- ExpenseClaim rows
- receipts
- policy documents
- vectors
- RAG state

The Auth Service answers:

> Who is this principal and what identity attributes are asserted?

The Core API answers:

> Is this principal allowed to perform this action on this expense resource in its current business state?

## 8. Service Boundary — AI Service

The AI Service owns AI application orchestration.

It owns:

- policy ingestion
- document parsing
- chunking
- embeddings
- vector retrieval
- lexical retrieval
- reranking
- prompt construction
- RAG orchestration
- RAG evaluation execution
- agent graph
- AI request telemetry
- multimodal extraction orchestration
- model-provider access policy

It must not become another business system of record.

The AI Service must not directly mutate Core database tables.

All claim-state changes pass through Core API capabilities.

## 9. Service Boundary — MCP Server

The MCP Server is an adapter and policy-aware integration boundary.

It owns:

- MCP protocol handling
- MCP tool schemas
- transport lifecycle
- tool-level timeout policy
- safe error mapping
- tool-call telemetry
- trusted identity propagation into Core API calls

It does not own:

- expense business logic
- user credentials
- claim authorization policy
- persistent claim state

MCP is introduced only in Phase 8.

Before Phase 8, the AI Agent may use internal HTTP-backed tools.

## 10. Data Ownership

Each service owns its data.

### Core logical ownership

    expense_claims
    expense_items
    receipts
    core_audit_events

### Auth logical ownership

    users
    refresh_sessions
    signing_key_metadata
    auth_audit_events

### AI logical ownership

    policy_documents
    policy_document_versions
    policy_chunks
    embeddings
    ingestion_runs
    evaluation_runs

Physical infrastructure may initially share a PostgreSQL server for cost efficiency, but logical ownership remains strict.

### Cross-Service Database Rule

No service may directly read or write another service's private tables.

Forbidden:

    AI Service
       |
       └── direct SQL to expense_claims

Required:

    AI Service
       |
       v
    Core API or approved MCP capability
       |
       v
    Core Database

The same rule applies between Auth Service and Core API.

## 11. Storage Architecture

### Relational data

Use PostgreSQL.

Core and Auth depend on relational transactions, constraints, and predictable consistency.

### Vector data

Use PostgreSQL plus pgvector initially.

Reasons:

- low operational complexity
- metadata filtering
- consistent PostgreSQL ecosystem
- adequate scale for this project
- no unnecessary vector-database product dependency

A separate vector database may replace pgvector only after a measurable requirement justifies it.

### Lexical search

Phase 6 should begin with PostgreSQL full-text search where sufficient.

OpenSearch is an optional later substitution if the learning objective or measured search requirements justify it.

### Binary objects

Receipt images and PDFs belong in object storage.

Development may use MinIO.

Production uses S3-compatible object storage.

Database rows store object metadata and keys, not large binary payloads.

## 12. Service Communication

Primary service-to-service communication is synchronous HTTP.

This is intentional because the current business workflows are request-response oriented and do not justify a message broker.

Do not add Kafka or RabbitMQ by default.

Protocols:

Auth Service:

    HTTP/JSON
    JWKS

Core API:

    HTTP/JSON

AI Service:

    HTTP/JSON
    optional SSE for streamed AI responses

MCP Server:

    MCP Streamable HTTP in deployed environments
    in-process or stdio for tests/local development when useful

## 13. API Contract Rules

Every public or cross-service HTTP endpoint must define:

- request schema
- response schema
- stable error schema
- authentication requirement
- authorization behavior
- idempotency semantics for writes where relevant

Recommended error shape:

~~~json
{
  "code": "CLAIM_NOT_FOUND",
  "message": "Expense claim was not found",
  "request_id": "..."
}
~~~

Do not return raw framework exceptions or database errors.

## 14. Identity Architecture

Auth Service issues short-lived access tokens.

Core and AI Services validate them independently using Auth Service public keys.

They must not call Auth Service for every protected request.

    Client
      |
      | credentials
      v
    Auth Service
      |
      | access token
      v
    Client
      |
      +----------> Core API
      |
      +----------> AI Service

Core and AI validate:

    signature
    issuer
    audience
    expiration
    required claims

Then normalize identity into SecurityContext.

## 15. Security Context

Business code should depend on a typed internal identity model rather than raw JWT claims.

Example:

~~~python
class SecurityContext(BaseModel):
    user_id: UUID
    role: Role
    manager_id: UUID | None
    department: str | None
~~~

This keeps authorization logic independent from token serialization details.

## 16. Authorization Architecture

Authorization is layered.

### Layer 1 — Authentication

Is the identity valid?

### Layer 2 — Role authorization

Does the principal have the broad business capability?

### Layer 3 — Resource authorization

Does this principal own or manage the target claim?

### Layer 4 — Workflow authorization

Is the requested action valid in the current claim state?

Example manager approval:

    role == MANAGER
    AND claim.manager_id == user.id
    AND claim.employee_id != user.id
    AND claim.status == SUBMITTED

An LLM must never be the authorization authority.

## 17. AI-to-Core Identity Propagation

Phase 5 tools and Phase 8 MCP tools operate on behalf of the authenticated user.

The model must never receive raw bearer credentials in prompt-visible context.

Required flow:

    user token
       |
       v
    trusted AI runtime
       |
       v
    validated SecurityContext
       |
       v
    trusted delegated request context
       |
       v
    Core API
       |
       v
    authorization

The model proposes a capability.

Trusted runtime supplies identity.

Core API authorizes the resource operation.

## 18. Basic RAG Architecture

Ingestion:

    Approved Policy Source
        |
        v
    Extraction
        |
        v
    Chunking
        |
        v
    Embeddings
        |
        v
    Vector Index

Query:

    User Question
        |
        v
    Query Embedding
        |
        v
    Retrieval
        |
        v
    Context Builder
        |
        v
    LLM
        |
        v
    Answer + Citations

Every retrievable chunk retains provenance.

Minimum metadata:

- document_id
- document_version
- title
- effective_date
- region
- policy_type
- chunk_id
- source checksum

## 19. Advanced Retrieval Architecture

Phase 6:

    Query
      |
      v
    Retrieval Router
      |
      +------ Dense Retrieval
      |
      +------ Lexical Retrieval
      |
      v
    Fusion
      |
      v
    Reranker
      |
      v
    Final Context

The Agent invokes one logical policy-search capability.

Agent orchestration must not depend on the internal search-engine implementation.

## 20. Agent Architecture

ExpenseFlow uses one primary agent.

Do not introduce multi-agent architecture without a requirement.

Minimal graph:

    START
      |
      v
    route request
      |
      +--> policy evidence
      |
      +--> claim evidence
      |
      +--> both
      |
      v
    synthesize
      |
      v
    END

Mandatory execution bounds:

- maximum steps
- maximum tool calls
- request timeout
- token budget
- retrieval result limit

No unbounded planner loop.

## 21. Human-Control Architecture

Classify actions by consequence.

### Informational

Examples:

- explain policy
- summarize own claim

May execute autonomously within permissions.

### Low-risk or reversible write

Example:

- create draft claim

Requires clear user intent.

### Consequential workflow write

Example:

- submit claim

Requires explicit confirmation immediately before execution.

### Organizational decision

Examples:

- manager approval
- rejection on behalf of manager
- reimbursement

Not exposed as agent tools in this project.

## 22. Multimodal Architecture

Receipt processing must not bypass Core authorization.

    User
      |
      v
    Core API upload
      |
      v
    Object Storage
      |
      v
    Receipt Metadata
      |
      v
    Authorized AI fetch
      |
      v
    Multimodal extraction
      |
      v
    Structured Receipt Facts
      |
      v
    Policy Retrieval
      |
      v
    Grounded Assessment

Model-extracted values are untrusted derived data until validated.

They must not automatically overwrite authoritative claim values.

## 23. MCP Architecture

Production path:

    Agent
      |
      v
    MCP Client
      |
      v
    MCP Server
      |
      v
    Core API
      |
      v
    Business Rules + Authorization
      |
      v
    Core Database

MCP tool descriptions are not security controls.

Tool availability is allowlisted by trusted runtime configuration.

## 24. LLM Security Architecture

By Phase 9, the AI path should conceptually follow:

    Request
      |
      v
    Authentication
      |
      v
    Authorization
      |
      v
    Input Controls
      |
      v
    Agent / RAG Runtime
      |
      +--> permission-aware retrieval
      |
      +--> bounded tools
      |
      v
    Secure Context Builder
      |
      v
    LLM Gateway
      |
      v
    Structured Output Validation
      |
      v
    Output Security
      |
      v
    Response

Critical invariant:

> The LLM only receives data that trusted preceding layers have already allowed.

## 25. Secure Context Builder

A dedicated component owns final model-context assembly.

Responsibilities:

- enforce context-size budget
- preserve provenance
- separate trusted instructions from untrusted data
- remove secrets
- normalize safe structured context

It is not an authorization engine.

Unauthorized data must be rejected before reaching this component.

## 26. LLM Gateway

All model-provider calls should eventually pass through one application abstraction.

Responsibilities:

- approved-model allowlist
- provider routing if later needed
- token limits
- timeout
- safe retry rules
- usage and cost collection
- logging redaction
- model/version attribution

Business modules should not scatter direct provider SDK calls.

## 27. Observability Architecture

All deployable components emit OpenTelemetry-compatible telemetry.

A request should preserve correlation across:

    Client
      |
    AI API
      |
    Agent
      |
    MCP
      |
    Core API
      |
    Database

Minimum correlation fields:

- trace_id
- span_id
- request_id
- service name
- operation name

Do not use sensitive business payloads as identifiers.

## 28. Telemetry Types

### Traces

Required where applicable for:

- HTTP requests
- database operations
- retrieval
- reranking
- model calls
- agent routing
- tool calls
- MCP calls

### Metrics

At minimum:

- request rate
- error rate
- latency
- model token usage
- model cost
- retrieval latency
- tool latency
- authorization/security denials

### Logs

Use structured JSON logs with request/trace correlation.

## 29. Audit vs Operational Telemetry

Operational telemetry answers:

> Why is the system slow or failing?

Audit answers:

> Who attempted or performed a business or security action?

Normal application logs are not a substitute for durable audit records.

## 30. Resilience Rules

Every network call must define:

- timeout
- retry policy
- failure behavior

Rules:

- never retry authorization failures
- never retry validation failures
- safe reads may use bounded retry
- write retry requires idempotency
- no recursive agent recovery loops
- dependency failure must not weaken security

## 31. Idempotency

Writes exposed through agent or MCP require idempotency where duplicate execution may be harmful.

Important examples:

- create draft
- submit claim

An ambiguous timeout must not produce uncontrolled duplicate state transitions.

## 32. Configuration and Secrets

Each service owns typed configuration.

Sources:

1. environment variables
2. production secret manager
3. safe non-sensitive local defaults

No production secret may be committed.

Every service should provide an environment example file with placeholders.

## 33. Local Development Topology

Use Docker Compose for infrastructure.

Applications may run directly on the host during active development.

Example:

    Developer Machine
    ├── core-api
    ├── auth-api
    ├── ai-api
    ├── mcp-server
    │
    └── Docker Compose
        ├── PostgreSQL
        ├── pgvector
        ├── MinIO
        └── observability components as introduced

Only start infrastructure required by the current phase.

## 34. Production Deployment Model

Every service must be independently containerizable.

Deployable units:

- core-api
- auth-api
- ai-api
- expense-core-mcp

Infrastructure dependencies:

- PostgreSQL
- object storage
- telemetry backend

A production platform may be Kubernetes, ECS, Nomad, or another managed container runtime.

Application code must not depend on Kubernetes-specific APIs.

## 35. Monorepo Structure

Target structure as capabilities appear:

    expenseflow/
    ├── services/
    │   ├── core-api/
    │   ├── auth-api/
    │   └── ai-api/
    │
    ├── mcp/
    │   └── expense-core-mcp/
    │
    ├── evals/
    │   ├── datasets/
    │   ├── rag/
    │   ├── agent/
    │   └── security/
    │
    ├── knowledge/
    │   └── expense-policies/
    │
    ├── infra/
    │   ├── compose/
    │   └── observability/
    │
    ├── specs/
    └── README.md

Do not create empty future-phase directories only to match this diagram.

## 36. Shared-Code Policy

Avoid building a large internal shared framework.

Acceptable shared code:

- stable DTO package when genuinely useful
- telemetry bootstrap
- small security primitives
- testing helpers

Do not share:

- SQLAlchemy models across service boundaries
- repositories
- database sessions
- service internals

Shared code must not erase ownership.

## 37. Architecture Evolution by Phase

| Phase | Architecture Delta |
|---|---|
| 1 | Core API + PostgreSQL |
| 2 | Auth Service + JWT/JWKS + resource authorization |
| 3 | AI Service + policy ingestion + pgvector |
| 4 | RAG evaluation + OpenTelemetry observability |
| 5 | Bounded agent runtime + internal tools |
| 6 | Adaptive retrieval + lexical retrieval + reranking |
| 7 | Object storage + multimodal receipt processing |
| 8 | MCP Server between Agent and Core capability surface |
| 9 | LLM security controls + adversarial regression suite |
| 10 | Agent runtime policy guard + confirmations + agentic security tests |

Every phase should modify the smallest practical part of the architecture.

## 38. Architecture Invariants

### INV-01

Core API remains the system of record for expense business state.

### INV-02

Auth Service remains the credential authority.

### INV-03

AI Service never directly writes Core database tables.

### INV-04

No service directly reads another service's private database tables.

### INV-05

Authorization is never delegated to an LLM.

### INV-06

Prompt text is never the only control preventing a business action.

### INV-07

Credentials remain outside model-visible prompt and tool arguments.

### INV-08

Every consequential action is attributable to an authenticated actor.

### INV-09

Retrieved data is authorized before entering model context.

### INV-10

LLM output is untrusted until validated for its downstream consumer.

### INV-11

Agent execution is bounded.

### INV-12

Architecture complexity is introduced only when a measurable requirement needs it.

## 39. Architecture Review Checklist

Before accepting an architecture change, ask:

1. Which service owns this capability?
2. Does this create direct database coupling?
3. Is identity preserved across the boundary?
4. Where is authorization enforced?
5. Can an LLM bypass it?
6. Is the new dependency actually required?
7. What happens when the dependency fails?
8. How will the call be traced?
9. Does the write require idempotency?
10. Does this violate an architecture invariant?
11. Could a simpler design satisfy the requirement?
12. Which phase requirement justifies the complexity?

If the last question has no answer, the component probably does not belong in the current phase.

## 40. Web Client Boundary

The supported browser client is a Next.js web application under:

    apps/web/

It is a presentation layer plus a thin Backend-for-Frontend boundary.

Browser flow:

    Browser
      |
      | same-origin request
      v
    Next.js Web + Route Handlers
      |
      +--> Auth Service
      +--> Core API
      +--> AI Service

Client rules:

- browser JavaScript must not store bearer or refresh tokens in persistent browser storage
- Route Handlers may hold HttpOnly cookie session credentials and forward bearer identity server-side
- Next.js must not duplicate Core business rules
- frontend role checks are user-experience controls only, never authorization
- Core and AI Services remain independently protected
- generated OpenAPI contracts should be used to reduce API-type drift
- AI output is untrusted and must be rendered safely
- consequential agent writes require explicit client confirmation as specified in Phase 10

The web client is optional in Phase 1 to preserve the minimum-code learning objective and becomes a first-class deployable application from Phase 2.

Detailed client rules are defined in:

    specs/00-client.md

## 41. Definition of Done

This architecture is correctly followed when ExpenseFlow can evolve through all ten phases without replacing its fundamental ownership model:

    Auth Service owns identity
            +
    Core API owns expense business state
            +
    AI Service owns AI orchestration
            +
    MCP Server exposes bounded Core capabilities
            +
    trusted runtime layers enforce security

Capability grows over time; ownership and trust boundaries remain explicit.
