# Phase 3 — Basic RAG in the AI Service

## 1. Purpose

Introduce a dedicated AI Service that answers employee questions about **expense reimbursement policy** using Retrieval-Augmented Generation.

Keep the use case intentionally narrow:

> Answer policy questions using approved ExpenseFlow policy documents and return source citations.

No agent, no MCP, no hybrid retrieval, no reranking, no multimodal behavior yet.

## 2. Architectural Change

    Client
      |
      +------> Auth Service
      |
      +------> Core API
      |
      +------> AI Service
                  |
                  +---- Embedding model
                  |
                  +---- Vector store
                  |
                  +---- LLM

The AI Service must use the existing access token validation approach from Phase 2.

The AI Service owns its ingestion state and vector data. It must not read the Core API database directly.

## 3. Business Use Case

Example questions:

- What is the hotel reimbursement limit in Singapore?
- Is airport taxi reimbursable?
- What evidence is required for a meal claim?
- Can I claim client entertainment expenses?
- When is manager pre-approval required?

The service answers policy questions only.

It must not approve claims, modify claims, submit claims, or reimburse claims.

## 4. Knowledge Corpus

Create a small, controlled corpus of approximately 10–30 documents.

Suggested document set:

- Global Expense Policy
- Travel Policy
- Hotel Policy
- Meal Policy
- Ground Transportation Policy
- Client Entertainment Policy
- Receipt and Evidence Policy
- Regional Policy — Vietnam
- Regional Policy — Singapore
- Regional Policy — United States

Documents should be stored in a repository-owned knowledge directory for reproducible learning.

Each source document requires metadata:

- document_id
- title
- version
- effective_date
- region
- policy_type
- source_path
- checksum

Do not ingest arbitrary user uploads in this phase.

## 5. RAG Pipeline

Required flow:

    Query
      |
      v
    Validate request
      |
      v
    Create query embedding
      |
      v
    Vector similarity search
      |
      v
    Top-K chunks
      |
      v
    Prompt construction
      |
      v
    LLM generation
      |
      v
    Answer + citations

The system must retain a distinction between:

- user question
- retrieved policy content
- system instructions

## 6. Ingestion Pipeline

Required ingestion steps:

1. Load approved source documents.
2. Extract text.
3. Normalize metadata.
4. Split text into chunks.
5. Generate embeddings.
6. Store chunks, embeddings, and metadata.
7. Record ingestion version and source checksum.

A simple recursive text splitter is acceptable initially.

Chunk size and overlap must be configuration values, not hidden constants.

## 7. Storage

Prefer a low-complexity vector store.

A valid reference approach is PostgreSQL plus pgvector so the project does not introduce another infrastructure product without need.

Requirements:

- AI Service owns its vector tables/schema.
- Core API does not query vector tables.
- Source metadata is stored with every chunk.
- Re-ingestion must not create uncontrolled duplicate chunks.
- Document version changes must be distinguishable.

## 8. Query API

POST /ai/query

Example request:

~~~json
{
  "question": "Can I claim a 450 USD hotel in Singapore?"
}
~~~

Example response:

~~~json
{
  "answer": "The policy states ...",
  "citations": [
    {
      "document_id": "singapore-travel-policy",
      "title": "Singapore Travel Policy",
      "version": "2026.1",
      "chunk_id": "..."
    }
  ]
}
~~~

Do not return raw embedding vectors.

## 9. Grounding Requirements

The generation prompt must require the model to:

- answer from retrieved policy context
- state when available context is insufficient
- avoid inventing policy limits
- cite the source documents used
- distinguish policy facts from general suggestions

The model must be allowed to abstain.

A response such as "The available policy sources do not establish this limit" is better than a fabricated answer.

## 10. Citation Requirements

Every factual policy answer must contain one or more citations.

A citation must map back to:

- document
- version
- chunk

The service must not generate fake source identifiers.

Citations come from retrieved metadata, not free-form model invention.

## 11. Authentication

The endpoint is protected.

The AI Service validates the existing ExpenseFlow access token.

In this phase, all authenticated users may query the approved policy corpus.

Fine-grained permission-aware retrieval is introduced during security hardening, but the data model must preserve metadata needed for future filtering.

## 12. Configuration

At minimum:

- LLM_MODEL
- EMBEDDING_MODEL
- VECTOR_DATABASE_URL
- RAG_TOP_K
- CHUNK_SIZE
- CHUNK_OVERLAP
- MAX_QUESTION_LENGTH

Do not hardcode API keys.

## 13. Example Retrieval Contract

~~~python
class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    document_version: str
    content: str
    score: float


class Retriever(Protocol):
    async def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        # The AI orchestration layer depends on a retrieval contract,
        # not directly on a specific vector-database SDK.
        ...
~~~

## 14. Minimal Observability

Phase 4 introduces serious observability. Phase 3 needs only enough to debug:

- request_id
- model name
- retrieval duration
- generation duration
- number of retrieved chunks
- token usage if provider returns it
- error type

Do not log entire confidential prompts by default.

## 15. Tests

Required:

### Ingestion

- source metadata is persisted
- changed version can be re-ingested
- duplicate ingestion does not duplicate active chunks uncontrollably

### Retrieval

- known query returns expected document in top K
- irrelevant query may return low-confidence context

### Generation

- answer contains citations
- no-context query can abstain
- citation identifiers are real retrieved identifiers

### API

- unauthenticated request is rejected
- malformed request is rejected
- valid question returns the defined schema

## 16. Acceptance Criteria

AC-01. A fresh setup can ingest the provided policy corpus.

AC-02. Each stored chunk retains document/version metadata.

AC-03. POST /ai/query performs vector retrieval and grounded generation.

AC-04. Policy answers contain real citations.

AC-05. The model can abstain when evidence is insufficient.

AC-06. Ingestion is repeatable and version-aware.

AC-07. AI Service has no direct dependency on the Core API database.

AC-08. No agent loop or tool calling exists yet.

## 17. Explicitly Out of Scope

Do not implement:

- RAGAS
- production tracing stack
- agentic routing
- Core API tools
- MCP
- BM25
- hybrid retrieval
- reranking
- query decomposition
- GraphRAG
- multimodal input
- OCR
- receipt understanding
- prompt-injection defense suite
- OWASP LLM hardening

Security basics such as authentication and secret handling remain mandatory, but full GenAI threat hardening is deferred to Phase 9.

## 18. Definition of Done

Phase 3 is complete when the system can reliably demonstrate the basic RAG chain:

    approved expense policies
        ->
    ingestion and chunking
        ->
    embeddings
        ->
    vector retrieval
        ->
    grounded generation
        ->
    answer with verifiable citations

The learner should be able to inspect every step rather than treating RAG as one opaque library call.

## Front-end Specification

### Goal

Add a focused policy-question experience that makes retrieval evidence visible.

### Required route

    /assistant/policy

### Required UI

- policy question input
- submit/cancel state
- answer panel
- structured citation list
- citation detail showing document title, version, region/policy metadata when returned
- explicit no-answer/insufficient-evidence state
- request ID on errors for debugging

Do not build a general chatbot in this phase.

### Rendering rules

- model text is untrusted
- raw HTML is disabled
- citations come from structured response fields
- do not parse model prose to invent citation links
- external links use an allowlisted safe protocol

### Front-end acceptance criteria

FE-01. An authenticated user can ask a policy question from the browser.

FE-02. Every returned citation can be inspected independently from the generated prose.

FE-03. Insufficient evidence is visibly different from a successful grounded answer.

FE-04. The UI cannot approve, edit, submit, or reimburse a claim through AI.

