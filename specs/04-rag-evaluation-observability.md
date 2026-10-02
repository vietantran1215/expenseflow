# Phase 4 — RAG Evaluation and Observability

## 1. Purpose

Make the Phase-3 RAG system measurable.

This phase should add almost no user-facing business capability. The main outcome is the ability to answer:

- Is retrieval finding the right evidence?
- Is the answer grounded in that evidence?
- Is quality regressing?
- Where is latency spent?
- How much does a request cost?
- Which failure mode is responsible when an answer is bad?

Primary learning outcome:

> Replace subjective "the answers look good" judgment with repeatable offline evaluation, production telemetry, and regression gates.

## 2. Architecture Delta

    Query
      |
      v
    AI Service
      |
      +---- trace: request
      |      |
      |      +---- embedding span
      |      +---- retrieval span
      |      +---- generation span
      |
      +---- structured metrics/logs
      |
      +---- evaluation dataset
      |
      +---- RAGAS/offline evaluator

## 3. Evaluation Dataset

Create a version-controlled golden dataset.

Start with approximately 30–50 questions, not hundreds.

Each record should contain:

- id
- question
- expected_answer or reference facts
- expected_document_ids
- optional expected_chunk_ids
- category
- difficulty
- notes

Suggested categories:

- hotel limits
- meals
- transportation
- receipt requirements
- regional policies
- approval requirements
- insufficient-evidence cases
- conflicting-version cases

Include negative questions for which the system should abstain.

## 4. Metric Maturity Strategy

Do not introduce every metric at once.

### Stage A — RAG quality fundamentals

Start with:

- Faithfulness
- Answer Relevancy
- Context Precision
- Context Recall

Use RAGAS or an equivalent implementation.

Purpose:

- Faithfulness: does the answer stay supported by retrieved evidence?
- Answer Relevancy: does it answer the actual question?
- Context Precision: how much retrieved context is useful?
- Context Recall: did retrieval recover the needed evidence?

### Stage B — Retrieval diagnostics

Add only when retrieval tuning starts:

- Hit Rate
- Recall@K
- Precision@K
- MRR

These require labeled expected sources.

### Stage C — operational metrics

Track:

- request count
- error count
- end-to-end latency
- retrieval latency
- generation latency
- embedding latency
- input tokens
- output tokens
- estimated cost
- retrieved chunk count
- abstention rate

Do not confuse operational metrics with answer-quality metrics.

## 5. Evaluation Workflow

Required offline workflow:

    Versioned dataset
        |
        v
    Run current RAG configuration
        |
        v
    Capture answer + contexts
        |
        v
    Calculate metrics
        |
        v
    Produce report
        |
        v
    Compare with previous baseline

Every evaluation run must record configuration:

- LLM model
- embedding model
- chunk size
- chunk overlap
- top K
- prompt version
- corpus version
- code commit where practical

Otherwise a metric number is not reproducible.

## 6. Baselines and Gates

The first run establishes a baseline.

Do not invent arbitrary "enterprise-grade" thresholds before observing the dataset.

After a baseline exists, define regression rules such as:

- no statistically meaningful drop in Faithfulness
- no unacceptable decrease in Context Recall
- no major P95 latency regression
- no large cost/query regression without approved trade-off

A pull request may run a smaller smoke evaluation set. A scheduled or release evaluation can run the full set.

## 7. Observability

Use OpenTelemetry-compatible tracing.

Minimum trace structure:

    ai.query
      |
      +-- embed.query
      |
      +-- retrieve.vector
      |
      +-- prompt.build
      |
      +-- llm.generate

Each trace should include safe metadata:

- request_id
- trace_id
- model
- embedding model
- top_k
- retrieved document IDs
- latency
- token counts
- status
- error type

Do not store full sensitive document chunks in trace attributes by default.

## 8. Structured Logging

Logs should be structured JSON.

Minimum fields:

- timestamp
- level
- service
- request_id
- trace_id
- event_name
- duration_ms
- outcome

No:

- access tokens
- API keys
- raw Authorization headers
- full confidential policy content by default

## 9. Metrics

Expose or export metrics suitable for a dashboard.

Minimum RED-style API metrics:

- request rate
- error rate
- duration

AI-specific:

- retrieval latency
- LLM latency
- embedding latency
- input/output tokens
- estimated cost
- retrieval result count
- abstention count

## 10. Dashboard

One dashboard is enough.

It should answer:

1. Is the AI endpoint healthy?
2. Is latency worsening?
3. Is the LLM provider failing?
4. Is retrieval slow?
5. Is token cost increasing?
6. Did error rate change after a deployment?

Do not build a large observability platform UI.

## 11. Example Evaluation Record

~~~python
class EvaluationCase(BaseModel):
    id: str
    question: str
    expected_answer: str | None = None
    expected_document_ids: list[str]
    category: str
    should_abstain: bool = False
~~~

## 12. Required Reports

Produce a machine-readable report and a human-readable summary.

Human summary should include:

- dataset version
- RAG configuration
- per-metric average
- failed cases
- notable regressions
- latency summary
- token/cost summary

Keep the underlying per-case results so averages cannot hide important failures.

## 13. Testing

Required:

- tracing exists for successful requests
- tracing records failures
- token counts are captured when available
- logs do not contain bearer tokens
- evaluator can run from a clean environment
- evaluation results are reproducible with the same configuration
- regression comparison works

## 14. Acceptance Criteria

AC-01. A version-controlled evaluation dataset exists.

AC-02. An automated evaluation command produces Faithfulness, Answer Relevancy, Context Precision, and Context Recall.

AC-03. Retrieval metrics can be added using labeled sources without redesigning the dataset.

AC-04. Every query emits trace spans for embedding, retrieval, and generation.

AC-05. Dashboard exposes request health, latency, errors, and AI cost signals.

AC-06. Evaluation output records the RAG configuration used.

AC-07. At least one regression gate compares a candidate configuration with a stored baseline.

AC-08. Sensitive tokens and full confidential content are not logged by default.

## 15. Explicitly Out of Scope

Do not add:

- new business workflow
- agent routing
- tool calling
- MCP
- hybrid retrieval
- reranking
- multimodal processing
- generic AIOps
- automated prompt optimization
- full online A/B experimentation

## 16. Definition of Done

Phase 4 is done when a bad RAG answer can be investigated using evidence:

    bad answer
       |
       +--> evaluation case
       +--> retrieved contexts
       +--> retrieval metrics
       +--> generation/faithfulness metrics
       +--> trace
       +--> latency and token usage

The system is no longer evaluated by intuition alone.

## Front-end Specification

### Goal

Keep business UX nearly unchanged while making request quality and observability diagnosable during development.

### Required UI delta

Add a development-only diagnostics surface available through a feature flag.

It may show only structured metadata already exposed safely by the backend, such as:

- request_id
- trace_id
- total latency
- retrieval latency
- generation latency
- retrieved chunk count
- model name/version
- token/cost metadata when available
- abstention/result status

Do not expose hidden prompts, secrets, bearer tokens, or model chain-of-thought.

### Optional route

    /diagnostics

This route is for learning/development and may summarize recent evaluation-run results only if the backend exposes a supported read API.

Do not build a second Grafana.

### Front-end acceptance criteria

FE-01. A learner can correlate a browser request with backend trace/request identifiers.

FE-02. Diagnostics can be disabled entirely in production configuration.

FE-03. Client telemetry never records passwords, tokens, raw receipts, or complete sensitive AI context.

FE-04. No new user-facing business workflow is introduced.

