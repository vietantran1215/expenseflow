# Phase 10 — Secure the Agentic Application Against OWASP Top 10 for Agentic Applications 2026

## 1. Purpose

Harden the ExpenseFlow agent and MCP integration against the current **OWASP Top 10 for Agentic Applications 2026**.

This is the final security phase. It must not add business features simply to make the architecture look more agentic.

Official baseline:

- OWASP Top 10 for Agentic Applications 2026
- https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/

The list used by this specification is:

1. ASI01: Agent Goal Hijack
2. ASI02: Tool Misuse and Exploitation
3. ASI03: Identity and Privilege Abuse
4. ASI04: Agentic Supply Chain Vulnerabilities
5. ASI05: Unexpected Code Execution (RCE)
6. ASI06: Memory & Context Poisoning
7. ASI07: Insecure Inter-Agent Communication
8. ASI08: Cascading Failures
9. ASI09: Human-Agent Trust Exploitation
10. ASI10: Rogue Agents

## 2. Security Principle

The final ExpenseFlow agent follows:

> Least privilege + least agency + explicit policy enforcement + human control for consequential actions + full observability.

An agent is not trusted merely because it was given a system prompt.

## 3. Final Agent Boundary

    User
      |
      v
    Authenticated AI API
      |
      v
    Agent Policy / Runtime Guard
      |
      v
    Bounded Agent Graph
      |
      +--> Secure RAG
      |
      +--> MCP Client
               |
               v
          MCP Server
               |
               v
          Core API AuthZ
      |
      v
    Structured Response

Cross-cutting:

- identity
- budgets
- audit
- trace
- approval gates
- kill/stop controls

## 4. ASI01 — Agent Goal Hijack

### ExpenseFlow scenarios

- malicious receipt tells the agent to submit another claim
- poisoned policy tells the agent to ignore authorization
- user asks the agent to change its goal from "explain" to "reimburse"
- tool result contains adversarial instructions

### Required controls

- fixed high-level agent purpose
- bounded graph routes
- untrusted content tagged/separated
- tool results treated as data, not trusted instructions
- no dynamic system-goal replacement from retrieved content
- policy checks before every write tool
- step/tool limits
- adversarial goal-hijack tests

A hijacked model response must not redefine the actual runtime policy.

## 5. ASI02 — Tool Misuse and Exploitation

### ExpenseFlow scenarios

A legitimate submit tool is invoked when the user only asked:

> "Is my claim ready to submit?"

### Required controls

- distinguish informational intent from action intent
- separate read and write tools
- write actions require explicit user intent
- confirmation step before consequential write
- strict schemas
- idempotency
- per-tool authorization
- tool-specific rate/size limits
- audit every write
- no generic arbitrary HTTP/filesystem/shell tools

### Example control flow

    Agent proposes submit
        |
        v
    Runtime policy check
        |
        v
    Explicit user confirmation
        |
        v
    Authorization
        |
        v
    submit_expense_claim
        |
        v
    Audit

## 6. ASI03 — Identity and Privilege Abuse

### Risks

- model attempts to act as another employee
- MCP uses a privileged service credential for all users
- delegated identity is lost between AI Service, MCP, and Core API
- agent gains broader authority than the initiating user

### Required controls

- end-user identity propagated through trusted runtime
- least-privilege service identity
- user authorization remains effective at Core API
- no model-visible credential
- no shared "god token"
- short-lived service credentials where applicable
- audience-restricted tokens
- identity included in audit trail
- explicit machine identity separate from user identity

Effective permission must be no broader than the allowed intersection of service and user authority.

## 7. ASI04 — Agentic Supply Chain Vulnerabilities

### Scope

Protect:

- MCP server code
- MCP client/SDK
- tool schemas/manifests
- agent framework
- model provider
- model configuration
- container images
- dependencies
- RAG sources

### Required controls

- pin dependencies
- SBOM
- vulnerability scanning
- approved MCP servers only
- no runtime discovery of arbitrary third-party MCP servers
- tool-schema review
- integrity/provenance for deployment artifacts
- signed/verified build artifacts where platform supports it
- controlled dependency update process
- environment allowlist for external endpoints

## 8. ASI05 — Unexpected Code Execution (RCE)

ExpenseFlow does not need arbitrary code execution.

The strongest control is attack-surface elimination.

Required:

- no shell tool
- no Python eval/exec
- no dynamic code interpreter
- no model-generated SQL execution
- no model-controlled command arguments to OS processes
- safe file parsing libraries
- file-type and size validation
- containers run with minimal privileges
- read-only filesystem where practical
- network egress constrained where practical

If a later feature needs code execution, it requires a new isolated sandbox design and is outside this project.

## 9. ASI06 — Memory & Context Poisoning

### Architecture decision

Long-term autonomous agent memory is not required for ExpenseFlow.

Prefer:

- short-lived per-request/session state
- authoritative business state stored in Core API
- policy knowledge stored in governed RAG corpus
- no self-written long-term memory that can become an authorization source

### Controls

- separate conversation state from authoritative business facts
- validate persisted memory if any exists
- expire session state
- never persist credentials in memory
- provenance for stored context
- do not let model-generated summaries override Core API records
- poisoning tests across multi-turn conversations

## 10. ASI07 — Insecure Inter-Agent Communication

ExpenseFlow intentionally uses a single primary agent in this phase.

Therefore:

- there is no A2A channel
- no external agent can send trusted instructions
- no agent identity/protocol is exposed

This is a valid security control through attack-surface elimination.

If multi-agent behavior is introduced later, the architecture must add:

- authenticated agent identities
- message integrity
- sender authorization
- typed message schemas
- replay protection where needed
- bounded trust
- per-agent permissions
- communication audit

Until then, ASI07 is marked **Not Applicable by Design**, with this rationale documented and tested by confirming no inter-agent endpoint exists.

## 11. ASI08 — Cascading Failures

### ExpenseFlow scenarios

- LLM latency triggers repeated agent retries
- MCP timeout triggers duplicate submits
- retrieval failure causes repeated model calls
- Core API outage amplifies into retry storm
- provider failure exhausts worker capacity

### Required controls

- bounded retries with backoff
- request deadline propagation
- idempotency for writes
- circuit breaker/fail-fast behavior where justified
- concurrency limits
- queue/backpressure if asynchronous work is introduced
- maximum agent steps
- no recursive recovery loops
- dependency health visibility
- graceful degraded response

Failure must stop at a bounded point rather than propagate indefinitely.

## 12. ASI09 — Human-Agent Trust Exploitation

### Risks

The agent presents uncertain recommendations with excessive confidence, causing a user to submit an invalid claim.

### Required controls

- distinguish recommendation from authoritative approval
- cite evidence
- expose uncertainty
- require explicit confirmation for write actions
- clear UI wording for generated content
- no dark-pattern confirmation
- show the exact proposed action before execution
- preserve human ability to cancel
- high-impact actions remain human-controlled

The agent must not claim that a reimbursement is approved unless authoritative Core API state says so.

## 13. ASI10 — Rogue Agents

ExpenseFlow should not permit an agent to create, spawn, or reconfigure agents dynamically.

Required:

- fixed agent graph/configuration deployed from reviewed code
- no self-modification
- no dynamic tool installation
- no sub-agent spawning
- hard request lifetime
- hard step limits
- kill/abort support
- runtime policy independent from model output
- deployment/configuration changes require normal engineering controls

A model-generated instruction cannot modify the deployed agent policy.

## 14. Human Control Model

Classify actions.

### Tier A — Informational

Examples:

- explain policy
- summarize own claim
- compare receipt to policy

May execute autonomously within read permissions.

### Tier B — Reversible/low-consequence write

Example:

- create expense draft

Require clear user intent; confirmation policy may be product-configurable.

### Tier C — Consequential workflow write

Example:

- submit claim

Require explicit user confirmation immediately before execution.

### Tier D — Organizational decision

Examples:

- approve
- reject on behalf of manager
- reimburse

Not exposed to the agent in this project.

## 15. Runtime Policy Guard

Create an application-layer guard outside the model.

Responsibilities:

- allowlisted tools
- allowed action tier
- user-intent requirement
- confirmation state
- step/tool budgets
- delegated identity context
- deny-by-default behavior

Example:

~~~python
class ToolPolicyDecision(BaseModel):
    allowed: bool
    reason_code: str
    requires_confirmation: bool


async def authorize_tool_call(tool_name, args, runtime):
    # The model proposes; trusted application policy decides.
    ...
~~~

## 16. Agent Observability

Trace every agent request.

Required events/spans:

- agent.start
- route.decision
- tool.proposed
- tool.policy_decision
- user.confirmation_requested
- user.confirmation_received
- tool.executed
- tool.failed
- agent.terminated
- budget.exceeded

Track:

- step count
- tool count
- write-tool count
- denied tool count
- confirmation count
- timeout
- retries
- agent termination reason

Do not expose hidden chain-of-thought.

## 17. Agent Security Test Matrix

Minimum tests:

### ASI01
Indirect prompt in receipt attempts to change agent goal.

### ASI02
Informational question attempts to trigger submit tool.

### ASI03
Agent attempts claim access using another user's ID.

### ASI04
Unapproved MCP server/tool cannot be loaded.

### ASI05
Prompt requesting shell/code execution cannot reach any execution capability.

### ASI06
Poisoned previous-session text cannot override authoritative claim state.

### ASI07
No inter-agent endpoint/channel exists; N/A-by-design assertion documented.

### ASI08
Core API timeout does not create retry storm or duplicate submit.

### ASI09
Agent recommendation requires user confirmation before submit.

### ASI10
Prompt cannot add tools, spawn agents, modify graph, or extend its execution budget.

## 18. Failure-Injection Tests

Required:

- LLM provider timeout
- vector store timeout
- reranker timeout
- MCP timeout
- Core API timeout
- Auth/JWKS transient failure
- duplicate tool response
- malformed tool response
- user disconnect during confirmation
- budget exhaustion

Verify both safety and termination behavior.

## 19. Acceptance Criteria

AC-01. All ten Agentic Top 10 categories are explicitly assessed.

AC-02. ASI07 is documented as N/A by design unless inter-agent communication is actually introduced.

AC-03. Agent runtime enforces an allowlisted tool set outside the LLM.

AC-04. No model-visible credential grants authority.

AC-05. Tool permissions never exceed the effective authorized user/service scope.

AC-06. Informational prompts cannot silently execute consequential writes.

AC-07. submit_expense_claim requires explicit confirmation.

AC-08. approve/reject/reimburse remain unavailable to the agent.

AC-09. No shell, eval, arbitrary-code, or unrestricted HTTP tool exists.

AC-10. Agent execution is bounded by time, steps, calls, tokens, and cost controls.

AC-11. Dependency failures terminate safely without uncontrolled cascading retries.

AC-12. Agent decisions, tool proposals, policy decisions, confirmations, and executions are observable.

AC-13. Security regressions run automatically from a version-controlled adversarial suite.

## 20. Explicitly Out of Scope

Do not add:

- multi-agent architecture merely to cover ASI07
- autonomous manager approval
- autonomous reimbursement
- arbitrary browser automation
- arbitrary shell/code execution
- dynamic tool marketplace
- self-modifying agents
- persistent self-authored long-term memory

## 21. Definition of Done

Phase 10 is complete when ExpenseFlow's agent can be manipulated at the language-model level without that manipulation automatically becoming business authority.

The required security invariant is:

    model proposes
        ->
    trusted runtime evaluates
        ->
    user confirms when required
        ->
    service authorizes
        ->
    tool executes
        ->
    outcome is audited

The model is part of the decision workflow, never the final security boundary.

## Front-end Specification

### Goal

Make human control, runtime policy decisions, and bounded agent termination explicit in the browser.

### Required action UX

For every consequential proposed action, display:

- action name in user language
- target resource
- important arguments/effect
- whether confirmation is required
- expiration/invalid state if the proposal can no longer execute
- confirm and cancel controls with no dark-pattern default

The browser must never auto-confirm because:

- the model said the user approved
- a previous message contained "yes"
- a tool result requested confirmation
- a hidden HTML element changed state

### Required runtime states

The assistant UI must handle:

- tool denied by policy
- confirmation required
- confirmation expired
- user cancelled
- execution succeeded
- execution failed
- maximum steps exceeded
- timeout/deadline exceeded
- budget exceeded
- runtime terminated

Do not automatically restart terminated agent execution.

### Trust presentation

- generated recommendations are visually distinguishable from authoritative Core state
- authoritative claim status comes from Core/API structured data
- uncertainty and citations remain visible
- no UI wording may imply approval/reimbursement unless authoritative business state says so

### Front-end acceptance criteria

FE-01. submit_expense_claim requires a live backend-recognized confirmation proposal.

FE-02. Confirmation cannot be replayed after expiry or successful use.

FE-03. Policy denial is displayed as denial rather than retried until success.

FE-04. Agent termination/budget states end the browser workflow deterministically.

FE-05. Approve, reject, reimburse, shell execution, dynamic tool installation, and agent spawning have no browser action surface.
