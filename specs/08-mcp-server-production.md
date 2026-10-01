# Phase 8 — Production-Grade MCP Server for the Core Service

## 1. Purpose

Expose a small set of ExpenseFlow Core API capabilities through a Model Context Protocol server and integrate those capabilities into the existing AI Agent.

The goal is not to wrap every REST endpoint in MCP.

Primary learning outcome:

> Design an MCP tool boundary that preserves identity, authorization, schemas, reliability, observability, and safe write semantics while remaining usable by an agent.

## 2. Architecture Delta

Before:

    AI Agent
       |
       v
    Custom HTTP Tool Wrappers
       |
       v
    Core API

After:

    AI Agent
       |
       v
    MCP Client
       |
       v
    ExpenseFlow MCP Server
       |
       v
    Core API

The MCP Server is an integration boundary, not a second business-logic implementation.

Core business rules stay in the Core API.

## 3. Initial Tool Surface

Expose only four tools.

### get_expense_claim

Purpose:

- retrieve a single accessible claim

Input:

- claim_id

### list_my_expense_claims

Purpose:

- list claims accessible to the current employee

Input:

- status optional
- limit
- cursor/offset depending on Core API

### create_expense_draft

Purpose:

- create a DRAFT claim

Input:

- business_purpose
- items

Identity fields are not model-controlled.

### submit_expense_claim

Purpose:

- submit an existing DRAFT claim

Input:

- claim_id
- idempotency key supplied by trusted runtime or application layer

Do not expose:

- approve claim
- reject claim
- reimburse claim

Those are more consequential and not needed for the MCP learning objective.

## 4. Identity Model

The model must never receive a raw access token as a tool argument.

Bad pattern:

    tool(claim_id, access_token)

Required pattern:

    Agent model
       |
       v
    tool selection
       |
       v
    trusted MCP client/runtime context
       |
       +---- delegated user identity
       |
       v
    MCP Server
       |
       v
    Core API

Credentials belong to trusted transport/runtime state.

The model chooses what capability to request. It does not choose whose authority is used.

## 5. Authorization

MCP must not become an authorization bypass.

Rules:

- MCP Server authenticates the caller/runtime.
- User identity is propagated to Core API through an approved mechanism.
- Core API remains the final authority for resource/workflow authorization.
- Tool descriptions must not be treated as security controls.
- A manipulated LLM must still be unable to read or modify resources outside the user's permissions.

## 6. Tool Schemas

Every tool must use strict typed input and output schemas.

Example:

~~~python
class CreateExpenseDraftInput(BaseModel):
    business_purpose: str
    items: list[ExpenseItemInput]


class CreateExpenseDraftOutput(BaseModel):
    claim_id: UUID
    status: Literal["DRAFT"]
    total_amount: Decimal
~~~

Reject unknown dangerous fields such as:

- employee_id
- manager_id
- role
- status
- approved_by

## 7. Write-Safety Requirements

create_expense_draft and submit_expense_claim are write operations.

Required controls:

- explicit input schema
- idempotency
- authorization
- bounded timeout
- structured audit event
- no hidden retry for non-idempotent operations unless protected by idempotency key
- clear tool result stating whether state changed

The agent should not retry a write blindly after an ambiguous timeout.

## 8. Error Mapping

Map downstream errors into stable MCP-level errors.

Examples:

- CLAIM_NOT_FOUND
- CLAIM_NOT_ACCESSIBLE
- INVALID_CLAIM_TRANSITION
- CORE_SERVICE_UNAVAILABLE
- TOOL_TIMEOUT
- VALIDATION_ERROR

Do not return raw stack traces, database errors, or internal URLs to the model.

## 9. Timeouts and Retries

Every Core API call must have a timeout.

Retry policy:

- safe GET operations may use bounded retry with backoff
- writes must not retry unless idempotency protects them
- do not retry authorization failures
- do not retry validation failures
- circuit-break or fail fast when the Core API is clearly unavailable

## 10. Rate and Resource Limits

Protect the MCP Server with:

- request rate limits
- maximum tool input size
- maximum result size
- maximum concurrent downstream requests
- timeout budgets

Large claim lists must be paginated.

## 11. Observability

Every tool call should create a trace span.

Required attributes:

- tool_name
- request_id
- trace_id
- caller/user ID in safe form
- duration
- downstream status
- outcome
- retry count
- idempotency outcome for writes

Do not log access tokens or full sensitive claim content by default.

## 12. Audit

Write tools must generate a durable business/security audit trail through the appropriate service.

Minimum:

- actor
- action
- resource
- timestamp
- request/trace identifier
- outcome

MCP-specific operational logs are not a replacement for business audit events.

## 13. Health and Deployment

The MCP Server must expose enough operational health information to support production deployment.

Required:

- liveness
- readiness
- dependency readiness for Core API connectivity where appropriate
- configuration validation at startup
- graceful shutdown
- containerization
- environment-based configuration

The exact MCP transport should follow the current MCP SDK-supported production transport selected by the implementation.

## 14. Versioning

Tool names and schemas form a contract.

Requirements:

- do not silently change semantics
- additive optional fields are preferred over breaking changes
- breaking tool changes require a versioning/migration strategy
- tool descriptions are reviewed like API contracts

## 15. Agent Integration

Replace custom Core HTTP tool wrappers with MCP-backed tools.

The agent should still see a small stable capability set.

Agent graph behavior remains bounded.

The switch to MCP must not alter authorization behavior.

## 16. Example Trusted Tool Adapter

~~~python
async def call_get_expense_claim(
    claim_id: str,
    runtime: AgentRuntime,
):
    # The model provides only the business argument.
    # Trusted runtime carries identity and transport credentials.
    return await runtime.mcp.call_tool(
        "get_expense_claim",
        {"claim_id": claim_id},
        context=runtime.delegated_identity_context(),
    )
~~~

## 17. Reliability Tests

Required:

- Core API timeout
- Core API 5xx
- Core API 401/403/404
- duplicate create request with same idempotency key
- duplicate submit request
- MCP process restart
- large list response
- malformed tool input
- tool result schema mismatch
- downstream slow response

## 18. Security Tests

Required:

- model cannot provide another user's identity
- employee cannot access another employee's claim through MCP
- tool input cannot mass-assign protected fields
- raw bearer token never appears in model prompt
- authorization failure is not retried
- write tools are auditable
- unavailable Core API fails closed

## 19. Acceptance Criteria

AC-01. AI Agent discovers and calls Core capabilities through MCP.

AC-02. Exactly the approved tool set is exposed.

AC-03. Model-visible tool arguments contain no credentials.

AC-04. Core API authorization is preserved end to end.

AC-05. Write tools are idempotent or protected against unsafe retry.

AC-06. Every tool has a strict schema and stable error contract.

AC-07. Every tool invocation is traceable.

AC-08. MCP Server has health checks, startup validation, graceful shutdown, and container deployment.

AC-09. Tool contract changes have an explicit versioning policy.

AC-10. Failure of MCP does not weaken security controls.

## 20. Explicitly Out of Scope

Do not add:

- generic filesystem tools
- shell execution
- arbitrary HTTP fetch tool
- dynamic third-party MCP discovery
- multi-agent communication
- approval/reimbursement tools
- plugin marketplace

## 21. Definition of Done

Phase 8 is complete when MCP is a production integration boundary rather than a demo wrapper:

    agent intent
       ->
    typed MCP tool
       ->
    trusted identity propagation
       ->
    Core API authorization
       ->
    safe business action
       ->
    audit + telemetry

The Core API remains the source of truth for expense business logic.
