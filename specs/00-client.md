# ExpenseFlow — Web Client Specification

## 1. Purpose

This document defines the web client architecture for ExpenseFlow.

The client exists to make the ten backend and AI phases usable and demonstrable without turning the project into a frontend curriculum.

The web application is responsible for:

- presentation
- user interaction
- browser-session handling
- calling backend services through a thin Backend-for-Frontend boundary
- streaming AI responses
- receipt upload UX
- citations and evidence presentation
- explicit confirmation for consequential agent actions

The client is **not** responsible for:

- expense business rules
- authorization decisions
- password validation
- claim-state enforcement
- RAG retrieval logic
- agent policy
- MCP authorization
- security decisions that backend services must enforce

If this document conflicts with a phase specification, this document is the default client authority unless that phase explicitly records a client architecture change.

## 2. Client Architecture

Use one web application:

    apps/web/

Technology:

    Next.js 16
    React 19
    TypeScript

The web application uses the Next.js App Router.

Browser-facing architecture:

    Browser
      |
      | same-origin HTTPS
      v
    Next.js Web Application
      |
      +--> Route Handlers / thin BFF
              |
              +--> Auth Service
              |
              +--> Core API
              |
              +--> AI Service

The browser should not directly depend on service topology.

If Core API or AI Service URLs change, the browser routes do not need to change.

## 3. Why a Thin BFF

The web client uses Next.js Route Handlers as a thin Backend-for-Frontend layer.

The BFF exists to:

- keep access and refresh tokens out of JavaScript-accessible storage
- reduce browser CORS complexity
- normalize browser-specific session behavior
- centralize server-side API client configuration
- provide same-origin streaming endpoints
- avoid exposing internal service addresses to the browser

The BFF must stay thin.

It must not reimplement:

- expense workflow rules
- claim authorization
- user-role authorization
- RAG policy
- agent tool policy

Example:

    Browser
      |
      | POST /api/claims/123/submit
      v
    Next Route Handler
      |
      | Bearer access token from secure cookie
      v
    Core API
      |
      v
    authorization + business-state validation

If Core rejects the action, the BFF returns the Core result.

The BFF must not decide that the claim is allowed to submit.

## 4. Browser Authentication Model

### Login

Flow:

    Browser
      |
      | username + password
      v
    Next.js /api/auth/login
      |
      v
    Auth Service /auth/login
      |
      | access token + refresh token
      v
    Next.js server
      |
      +--> set HttpOnly access-token cookie
      |
      +--> set HttpOnly refresh-token cookie
      |
      v
    Browser session established

Tokens are never returned to client JavaScript.

### Cookie requirements

Authentication cookies must use:

- HttpOnly
- Secure in deployed environments
- SameSite=Lax by default
- narrow Path where practical
- explicit Max-Age/Expires
- no Domain widening unless deployment requires it

Never store access or refresh tokens in:

- localStorage
- sessionStorage
- IndexedDB
- React state
- URL parameters

## 5. Session Refresh

The Next.js server owns browser token refresh.

Flow:

    Browser request
       |
       v
    Next server detects expired/near-expired access token
       |
       v
    Auth Service /auth/refresh
       |
       v
    rotated refresh token + new access token
       |
       v
    update HttpOnly cookies
       |
       v
    continue request

Refresh-token rotation rules from Phase 2 remain authoritative.

The client must not weaken replay detection.

## 6. Logout

Browser calls:

    POST /api/auth/logout

Next.js server:

1. invokes Auth Service logout
2. clears local authentication cookies
3. returns a safe response even if cookie cleanup must occur after an upstream failure

Logout-all should call the corresponding Auth Service capability.

## 7. CSRF and Same-Origin Protection

Because browser authentication uses cookies to the Next.js BFF, all state-changing web endpoints require browser-origin protection.

Minimum controls:

- SameSite cookies
- verify Origin header for unsafe methods
- reject unexpected cross-origin mutation requests
- use CSRF token protection if deployment requirements exceed SameSite + Origin validation
- do not enable permissive CORS for BFF routes

Backend Core and AI Services continue to authenticate via bearer tokens received server-to-server from the BFF.

## 8. API Client Contracts

Do not hand-maintain duplicate TypeScript API interfaces when FastAPI OpenAPI already defines the contracts.

Generate TypeScript contracts from service OpenAPI documents.

Recommended:

    openapi-typescript
    openapi-fetch

Generated clients should live in a generated directory such as:

    apps/web/src/generated/

Do not manually edit generated files.

Example:

    Auth OpenAPI
        |
        v
    generate auth types

    Core OpenAPI
        |
        v
    generate core types

    AI OpenAPI
        |
        v
    generate ai types

Contract generation should be automated in development/CI.

## 9. Server-Side API Clients

Create one typed server-only client wrapper per backend service:

    src/server/api/auth.ts
    src/server/api/core.ts
    src/server/api/ai.ts

Responsibilities:

- base URL
- timeout
- request ID propagation
- bearer-token propagation
- safe error normalization
- OpenTelemetry propagation

Do not let Client Components import these modules.

Use the Next.js server-only boundary where appropriate.

## 10. Rendering Model

Default to Server Components.

Use Client Components only when browser interactivity is required.

### Server Components

Good use cases:

- claim list
- claim detail initial render
- static policy citation display
- user profile
- navigation shell

### Client Components

Use for:

- forms with immediate interaction
- AI token streaming
- receipt upload progress
- optimistic local UX where justified
- confirmation dialogs
- interactive evaluation/debug views if later required

Do not turn the entire application into a client-side SPA without reason.

## 11. Client State

Use the smallest possible state model.

Preferred order:

1. URL/search params
2. Server Component data
3. local component state
4. React context for small cross-cutting UI state

Do not introduce Redux or another global state library by default.

Backend business state must remain backend-owned.

## 12. Routes

Target application routes appear gradually.

### Authentication

    /login

### Expense claims

    /claims
    /claims/new
    /claims/[claimId]

### AI assistant

    /assistant

### Receipt analysis

Integrated into:

    /claims/[claimId]

or:

    /claims/[claimId]/receipts/[receiptId]

Do not create a large dashboard/navigation hierarchy unless business requirements justify it.

## 13. Phase 1 Client Scope

No custom web client implementation is required in Phase 1.

Use:

- FastAPI Swagger UI
- curl/HTTP client
- automated tests

Reason:

> Phase 1 explicitly optimizes for minimum code while learning Core API fundamentals.

The client architecture begins implementation in Phase 2.

## 14. Phase 2 Client Scope

Introduce:

    apps/web/

Minimum pages:

- Login
- My Claims list
- Claim detail
- Create Draft Claim
- Submit Claim
- Manager review controls when role permits
- Finance reimbursement control when role permits

Important:

UI role checks are presentation only.

Example:

    if role != MANAGER:
        hide Approve button

This improves UX but is not security.

Core API must still reject unauthorized approval attempts.

## 15. Phase 3 Client Scope

Add:

    /assistant

Minimum UI:

- question input
- answer
- citations
- loading/error state

Do not build conversation history, memory, or a chat-product clone yet.

The objective is to demonstrate RAG.

## 16. Phase 4 Client Scope

No new business UI is required.

Optionally add a development-only diagnostics view, but official evaluation output should remain generated by the evaluation pipeline rather than manually inspected through a dashboard.

## 17. Phase 5 Client Scope

Enhance Assistant to present safe agent execution information.

May display:

- "Searching expense policy"
- "Reading claim #..."
- "Combining claim and policy evidence"

Do not display:

- hidden chain-of-thought
- raw system prompt
- credentials
- internal security metadata

Tool execution summaries must be derived from trusted runtime events rather than fabricated model prose.

## 18. Phase 6 Client Scope

No major UI change.

Assistant continues to show answer and citations.

Retrieval strategy is primarily backend behavior.

A development/debug mode may display:

- retrieval strategy
- source ranks
- evaluation diagnostics

but this should not be exposed to normal users by default.

## 19. Phase 7 Client Scope

Add receipt upload and analysis.

Required UX:

- select/drop supported receipt
- validate obvious file constraints client-side for fast feedback
- upload progress
- server validation errors
- analysis status
- extracted structured fields
- extraction warnings
- policy assessment
- citations

Client-side validation is UX only.

The server remains authoritative for:

- media type
- file size
- authorization
- extraction schema
- policy decision support

## 20. Phase 8 Client Scope

No significant business UI change is required.

MCP is internal architecture between Agent and Core capabilities.

The user should not need to understand whether the agent called:

    custom HTTP tool

or:

    MCP tool

That is an internal integration concern.

## 21. Phase 9 Client Security Hardening

The client participates in LLM application security.

Required:

### Safe rendering

Treat AI output as untrusted.

- never render model HTML with unsafe raw HTML APIs
- sanitize any supported Markdown extensions
- validate URLs before rendering active links
- do not execute generated JavaScript
- do not map free-form AI output directly to browser actions

### Sensitive information

Do not expose:

- access token
- refresh token
- system prompts
- hidden retrieval context
- internal tool credentials
- unnecessary sensitive claim fields

### Citation UX

Citations must be visibly associated with claims in the answer.

A citation click should use trusted source metadata, not a model-generated arbitrary URL.

### Refusals and uncertainty

The UI must clearly render:

- insufficient evidence
- authorization denial
- model uncertainty
- system failure

Do not convert these into confident-looking answers.

## 22. Phase 10 Client Security Hardening

The client becomes part of human-agent control.

When the Agent proposes a consequential write such as:

    submit_expense_claim

the UI must show an explicit confirmation step.

Example:

    Submit expense claim?

    Claim: #123
    Total: 450 USD
    Action: Submit for manager review

    [Cancel] [Confirm Submit]

Requirements:

- action details come from trusted structured runtime data
- confirmation is bound to a specific pending action
- confirmation expires
- user may cancel
- repeated clicks must not create duplicate execution
- client must not claim success until Core API confirms success

Do not use vague confirmation text such as:

    "Continue?"

## 23. AI Streaming

Use Server-Sent Events or HTTP streaming through a same-origin Next.js route.

Flow:

    Browser
      |
      v
    Next.js /api/assistant/stream
      |
      v
    AI Service streaming endpoint

The browser must be able to cancel the request.

Cancellation should propagate downstream where practical.

Do not use WebSockets unless a later requirement needs bidirectional persistent communication.

## 24. Error Handling

The client must map stable backend error codes into user-facing messages.

Example:

    CLAIM_NOT_FOUND
       ->
    "This expense claim could not be found."

Do not expose:

- Python stack traces
- SQL errors
- internal service hostnames
- JWT validation internals
- raw LLM provider errors

Keep detailed diagnostics in backend observability.

## 25. Accessibility

Minimum target:

    WCAG 2.2 AA for core workflows

Required basics:

- semantic form labels
- keyboard accessibility
- visible focus
- accessible error messages
- sufficient contrast
- buttons use meaningful labels
- streaming status is announced appropriately

Accessibility is part of enterprise client quality, not optional polish.

## 26. Responsive Design

The web client must support:

- desktop
- tablet
- mobile

Design is mobile-friendly but desktop remains important because manager and Finance review workflows are enterprise tasks.

Avoid separate mobile and desktop applications.

## 27. UI Design Principle

UI should be functional and minimal.

The project is not a design-system exercise.

Do not add a large component framework solely for aesthetics.

Reusable local components are enough:

    Button
    Input
    Select
    FormField
    Alert
    Dialog
    ClaimStatus
    Citation
    ReceiptUpload

## 28. Testing

### Unit/component

Use:

- Vitest
- React Testing Library

Required for:

- form behavior
- error mapping
- confirmation behavior
- safe rendering
- permission-based presentation

### End-to-end

Use:

    Playwright

Critical flows:

1. Login
2. Create draft claim
3. Submit claim
4. Manager review
5. Finance reimbursement
6. Ask policy question
7. View citations
8. Upload and analyze receipt
9. Agent proposes submit
10. User confirms/cancels submit

E2E tests must not substitute for backend authorization tests.

## 29. Client Observability

Propagate:

- request ID
- W3C trace context where supported

Capture:

- client-visible request failures
- AI streaming failure
- upload failure
- unexpected UI exceptions

Do not send sensitive form values or AI context indiscriminately to frontend analytics.

## 30. Client Project Structure

Recommended structure:

    apps/web/
    ├── app/
    │   ├── login/
    │   ├── claims/
    │   ├── assistant/
    │   └── api/
    │       ├── auth/
    │       ├── claims/
    │       └── assistant/
    │
    ├── src/
    │   ├── components/
    │   ├── generated/
    │   ├── server/
    │   │   ├── api/
    │   │   ├── auth/
    │   │   └── observability/
    │   └── client/
    │
    ├── tests/
    ├── e2e/
    ├── package.json
    └── tsconfig.json

Avoid deep architecture layers in the frontend unless complexity actually appears.

## 31. Client Technology Stack

Baseline:

| Area | Technology |
|---|---|
| Runtime | Node.js 24 LTS |
| Framework | Next.js 16.3.x Active LTS |
| UI runtime | React 19.3 |
| Language | TypeScript 5.x |
| Routing | Next.js App Router |
| Browser/backend boundary | Next.js Route Handlers thin BFF |
| API contracts | OpenAPI-generated TypeScript |
| API client | openapi-fetch/native fetch |
| Styling | CSS Modules / modern CSS |
| State | React built-ins; no global state library by default |
| Streaming | SSE / Fetch streaming |
| Component tests | Vitest + React Testing Library |
| E2E | Playwright |
| Package manager | pnpm |
| Telemetry | OpenTelemetry-compatible server instrumentation |

Exact versions must be locked.

## 32. Client Security Invariants

### CLIENT-INV-01

Access and refresh tokens are never stored in JavaScript-readable persistent browser storage.

### CLIENT-INV-02

The UI is never an authorization boundary.

### CLIENT-INV-03

The BFF contains no duplicated expense business logic.

### CLIENT-INV-04

AI output is treated as untrusted content.

### CLIENT-INV-05

Model-generated text cannot directly execute browser or backend actions.

### CLIENT-INV-06

Consequential Agent writes require explicit trusted UI confirmation.

### CLIENT-INV-07

Browser code does not know internal database or MCP topology.

### CLIENT-INV-08

Generated OpenAPI contracts are not manually edited.

### CLIENT-INV-09

The client does not expose raw credentials, hidden prompts, or unrestricted retrieved context.

### CLIENT-INV-10

Backend success is the source of truth for whether a business action completed.

## 33. Definition of Done

The ExpenseFlow client is correctly designed when it remains a thin, secure presentation layer while the backend evolves from traditional APIs to RAG, Agents, MCP, and GenAI security.

The desired boundary is:

    User Interaction
       |
       v
    Next.js Presentation + Thin BFF
       |
       v
    Auth / Core / AI Services
       |
       v
    authoritative business and security decisions

The browser helps the user operate ExpenseFlow. It does not become a second backend.
