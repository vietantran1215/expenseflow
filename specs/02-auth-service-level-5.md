# Phase 2 — Enterprise Authentication & Authorization Service: FastAPI Level 5

## 1. Purpose

Add a production-oriented identity and access-control boundary to ExpenseFlow.

This phase is intentionally much deeper than Phase 1. The goal is not merely to make a login endpoint work. The goal is to understand enterprise authentication, token lifecycle, authorization, delegated identity, auditability, and secure integration between the Auth Service and Core API.

Primary learning outcome:

> Build and integrate an authentication service that can issue, rotate, revoke, validate, and audit credentials while ensuring ExpenseFlow business actions are authorized using both role and resource context.

## 2. Architectural Change

Before:

    Client
      |
      v
    Core API

After:

    Client
      |
      +------> Auth Service
      |           |
      |           +---- access token
      |
      v
    Core API
      |
      +---- verifies identity
      |
      +---- applies resource and workflow authorization

The Auth Service owns identity. The Core API owns expense business resources and must still make resource-level authorization decisions.

The Auth Service must not query the Core API database directly, and the Core API must not query the Auth Service database directly.

## 3. Roles

Only three business roles are needed:

- EMPLOYEE
- MANAGER
- FINANCE

Do not add a generic permission-management UI or arbitrary custom roles.

## 4. Identity Model

### User

Required fields:

- id: UUID
- username: unique string
- password_hash
- role: EMPLOYEE | MANAGER | FINANCE
- manager_id: nullable UUID
- department: string
- is_active: boolean
- token_version or equivalent revocation marker
- created_at
- updated_at

### Refresh Session

Required fields:

- id
- user_id
- token_family_id
- refresh_token_hash
- issued_at
- expires_at
- rotated_at
- revoked_at
- replaced_by_session_id
- client metadata kept minimal

Refresh tokens must not be stored in plaintext.

### Auth Audit Event

Minimum fields:

- id
- user_id if known
- event_type
- outcome
- request_id
- source IP or privacy-safe equivalent
- timestamp
- reason_code

Never store passwords or raw bearer tokens in audit records.

## 5. Authentication Requirements

### Password storage

Use a memory-hard password hashing algorithm such as Argon2id.

Requirements:

- unique salt handled by the password library
- no plaintext passwords
- no reversible encryption for user passwords
- password hash never returned by an API
- password verification must use the library's safe verification method

### Login

POST /auth/login

Successful login returns:

- access_token
- refresh_token
- token_type
- expires_in

Failed login must use a generic error response that does not reveal whether the username exists.

### Access token

Use asymmetric signing so downstream services can validate tokens without sharing the private signing key.

Required claims:

- iss
- aud
- sub
- role
- manager_id where applicable
- department
- iat
- exp
- jti

The signing algorithm must be explicitly allowlisted.

The Core API must verify:

- signature
- issuer
- audience
- expiration
- expected algorithm
- required claims

Decoding without validation is forbidden.

### JWKS

Expose a standard public-key endpoint, for example:

GET /.well-known/jwks.json

The private signing key remains only in the Auth Service.

Include key identifiers so key rotation is possible.

### Refresh token rotation

POST /auth/refresh

Every successful refresh must rotate the refresh token.

Old refresh tokens become unusable.

Refresh-token replay must revoke the token family or otherwise invalidate the compromised session lineage.

### Logout

POST /auth/logout

Revokes the current refresh session.

### Logout all sessions

POST /auth/logout-all

Revokes all refresh sessions for the current user.

### Current identity

GET /me

Returns only safe identity attributes required by clients.

## 6. Authorization Model

Role checks alone are insufficient.

ExpenseFlow requires three layers:

1. Role authorization
2. Resource authorization
3. Workflow-state authorization

### Employee rules

An EMPLOYEE may:

- create a claim for self
- list own claims
- read own claim
- edit own DRAFT claim
- submit own DRAFT claim

An EMPLOYEE may not:

- read another employee's claim
- choose employee_id for a newly created claim
- approve or reimburse a claim

After Phase 2, employee_id must be derived from authenticated identity.

### Manager rules

A MANAGER may:

- perform normal employee actions for own claims
- list claims assigned to the manager
- read assigned claims
- approve or reject an assigned SUBMITTED claim

A MANAGER may not:

- approve own claim
- approve a claim assigned to another manager
- approve a claim in the wrong state

### Finance rules

FINANCE may:

- read APPROVED claims
- mark an APPROVED claim as REIMBURSED

FINANCE may not bypass the manager approval state.

## 7. Authorization Decision Examples

Manager approval requires all conditions:

    user.role == MANAGER
    AND claim.manager_id == user.id
    AND claim.employee_id != user.id
    AND claim.status == SUBMITTED

A role-only check is a failed implementation.

Example:

~~~python
def can_manager_approve(claim, current_user):
    # Authorization combines identity, ownership/assignment,
    # separation of duties, and business state.
    if current_user.role != Role.MANAGER:
        return False

    if claim.manager_id != current_user.user_id:
        return False

    if claim.employee_id == current_user.user_id:
        return False

    if claim.status != ClaimStatus.SUBMITTED:
        return False

    return True
~~~

## 8. Core API Security Changes

Phase 1 allowed identity fields in requests because authentication did not exist. Phase 2 must remove that trust.

### Create claim

Client request must not select employee_id.

Core API assigns:

    employee_id = authenticated_user.sub

manager_id may be resolved from a trusted claim or by calling a safe identity endpoint, depending on implementation.

### Read claim

The Core API must query with resource constraints where practical.

Example:

~~~python
async def get_employee_claim(session, claim_id, employee_id):
    statement = (
        select(ExpenseClaim)
        .where(ExpenseClaim.id == claim_id)
        .where(ExpenseClaim.employee_id == employee_id)
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()
~~~

Do not load arbitrary employee data and then rely on the client not to guess identifiers.

### Unauthorized resource semantics

For cross-user object access, prefer a response that does not reveal whether an inaccessible claim exists. A 404 response is acceptable for hidden resources.

## 9. Service-to-Service Trust

The Core API must validate access tokens independently using the Auth Service public keys.

It must not call /auth/introspect on every request unless there is a deliberate reason, because that creates an unnecessary runtime dependency.

Required behavior:

- cache JWKS safely
- honor key identifiers
- refresh keys on unknown key id
- reject tokens when validation fails
- never fail open

## 10. Rate Limiting and Abuse Controls

Login must have basic anti-brute-force controls.

Minimum:

- per-account or username-based failure tracking
- per-source throttling where practical
- 429 after configured threshold
- audit failed logins
- avoid permanent denial-of-service through naive account lockout

The exact policy is configurable.

A suitable capstone default is a short rolling limit rather than a long permanent lock.

## 11. Secrets and Key Management

Configuration must come from environment or a secret manager abstraction.

At minimum:

- AUTH_PRIVATE_KEY or key path
- token issuer
- token audience
- access-token TTL
- refresh-token TTL
- DATABASE_URL

Repository may include .env.example only with placeholders.

Private keys, passwords, and real tokens must never be committed.

## 12. Audit Requirements

Mandatory audit events:

- LOGIN_SUCCESS
- LOGIN_FAILURE
- REFRESH_SUCCESS
- REFRESH_FAILURE
- REFRESH_REPLAY_DETECTED
- LOGOUT
- LOGOUT_ALL
- TOKEN_VALIDATION_FAILURE where useful
- ACCESS_DENIED for consequential Core operations
- CLAIM_APPROVED
- CLAIM_REJECTED
- CLAIM_REIMBURSED

Audit must be security-useful but privacy-aware.

Do not log:

- plaintext passwords
- password hashes
- access tokens
- refresh tokens
- Authorization headers

## 13. Required Endpoints

Auth Service:

- POST /auth/login
- POST /auth/refresh
- POST /auth/logout
- POST /auth/logout-all
- GET /me
- GET /.well-known/jwks.json
- GET /health

No self-registration is required. Seed users through migration or an admin bootstrap script.

Core API remains the owner of expense endpoints, but every protected endpoint now requires validated identity and authorization.

## 14. Threat Scenarios

TS-01. Invalid password -> 401 with generic message.

TS-02. Tampered JWT -> 401.

TS-03. Expired JWT -> 401.

TS-04. Token signed using an unexpected algorithm -> 401.

TS-05. Disabled user cannot establish a new session.

TS-06. Replayed refresh token is detected and the affected token family is revoked.

TS-07. Employee A requests Employee B claim -> no data disclosure.

TS-08. Employee tries to submit a claim on behalf of another employee -> denied.

TS-09. Manager A tries to approve Manager B's report -> denied.

TS-10. Manager tries to approve own claim -> denied.

TS-11. Finance attempts to reimburse SUBMITTED instead of APPROVED -> denied.

TS-12. Client submits employee_id, role, status, or manager_id through mass assignment -> rejected or ignored by an explicit schema policy.

TS-13. Login endpoint is brute-forced -> throttle applies and events are auditable.

TS-14. Logs are inspected -> no tokens, passwords, password hashes, or Authorization headers exist.

## 15. Security Tests

Required automated suites:

- password hashing behavior
- token signature validation
- issuer/audience validation
- expiration
- algorithm allowlist
- refresh rotation
- refresh replay
- logout revocation
- role checks
- object-level authorization
- separation of duties
- workflow authorization
- rate-limit behavior
- sensitive-log redaction

Negative authorization tests are mandatory.

## 16. Acceptance Criteria

AC-01. Passwords are never stored or logged in plaintext.

AC-02. Core API validates access tokens with public keys and never receives the Auth private signing key.

AC-03. Access tokens expire and invalid tokens are rejected.

AC-04. Refresh tokens rotate on every refresh.

AC-05. Reusing a rotated refresh token causes a security response rather than issuing another session.

AC-06. Employee identity is server-derived when creating claims.

AC-07. Employees cannot read or modify other employees' claims.

AC-08. Managers cannot approve their own claims or claims not assigned to them.

AC-09. Finance cannot bypass business workflow.

AC-10. Authorization failures are covered by automated tests.

AC-11. Security-sensitive events are auditable.

AC-12. No raw credential or bearer token appears in application logs.

AC-13. Key rotation is technically possible through JWKS and key identifiers.

AC-14. OpenAPI clearly marks protected endpoints.

## 17. Explicitly Out of Scope

Do not implement:

- SAML
- social login
- full external enterprise IdP integration
- MFA
- SCIM
- arbitrary policy-language UI
- custom role designer
- OAuth consent screens
- service mesh
- RAG
- LLM
- MCP

These may be realistic enterprise features, but they are not required to teach the security boundaries targeted by this phase.

## 18. Definition of Done

Phase 2 is complete when ExpenseFlow can prove:

    identity is authenticated
        ->
    credentials have a safe lifecycle
        ->
    downstream services validate identity
        ->
    every business action is authorized
        ->
    authorization includes resource and state context
        ->
    consequential actions are auditable

A working login page alone does not satisfy this phase.
