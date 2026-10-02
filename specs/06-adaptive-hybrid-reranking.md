# Phase 6 — Adaptive RAG, Hybrid Retrieval, and Reranking

## 1. Purpose

Improve retrieval quality without changing the business domain.

This phase upgrades the AI Service so it can choose a retrieval strategy based on the query and combine semantic and lexical signals before reranking candidates.

Primary learning outcome:

> Understand when vector-only retrieval is insufficient, how to combine dense and lexical retrieval, how reranking changes precision, and how to prove the improvement using the evaluation system built in Phase 4.

## 2. Why This Phase Exists

Expense policies contain many exact terms that semantic search may not rank well:

- policy codes such as TRV-0042
- employee grades such as L6
- currency values such as USD 450
- country names
- exact allowance labels such as PER-DIEM
- internal policy abbreviations
- effective dates

A query such as:

> "What does TRV-0042 say about L6 hotel limits in Singapore?"

should not depend on embeddings alone.

## 3. Architecture Delta

Before:

    Query
      |
      v
    Vector Retrieval
      |
      v
    Top K
      |
      v
    LLM

After:

    Query
      |
      v
    Retrieval Strategy Router
      |
      +--> Dense Retrieval
      |
      +--> Lexical/BM25 Retrieval
      |
      v
    Candidate Fusion
      |
      v
    Reranker
      |
      v
    Final Context
      |
      v
    LLM

The existing Agent from Phase 5 can call this retrieval pipeline as one policy-search capability.

## 4. Adaptive Retrieval Routes

Required routes:

- NO_RETRIEVAL
- DENSE
- LEXICAL
- HYBRID

Example routing logic:

- general product explanation -> NO_RETRIEVAL
- natural-language policy question -> DENSE
- exact policy code or exact identifier -> LEXICAL
- mixed semantic + exact constraints -> HYBRID

The router must return a structured decision.

Example:

~~~json
{
  "strategy": "HYBRID",
  "reason_code": "SEMANTIC_AND_EXACT_TERMS"
}
~~~

Do not let the router invent arbitrary retriever names.

## 5. Dense Retrieval

Reuse the existing vector search.

Required:

- configurable top K
- metadata filtering
- stable result contract
- score retained for debugging

## 6. Lexical Retrieval

Implement BM25 or an equivalent lexical retrieval method.

Valid implementation options include:

- PostgreSQL full-text search where sufficient
- OpenSearch/Elasticsearch BM25
- a local BM25 implementation for learning

Choose the simplest implementation that supports reproducible evaluation.

The lexical index must preserve the same document/chunk identifiers as the vector index so results can be fused.

## 7. Hybrid Fusion

Combine dense and lexical candidate sets.

Recommended baseline:

- Reciprocal Rank Fusion (RRF)

Reason:

- simple
- score-scale independent
- easy to explain
- easy to compare with vector-only retrieval

Do not prematurely build a learned fusion model.

Required output:

- candidate chunk ID
- dense rank if present
- lexical rank if present
- fused rank/score

## 8. Reranking

Retrieve broadly, then rerank narrowly.

Example:

    Dense Top 20
       +
    Lexical Top 20
       |
       v
    Fusion
       |
       v
    Top 20–30 candidates
       |
       v
    Reranker
       |
       v
    Final Top 5

The reranker may be:

- a cross-encoder
- a provider rerank model
- an LLM-based reranker if cost is acceptable

Reranking configuration must be explicit.

## 9. Metadata Filtering

Policy metadata should support at least:

- region
- policy_type
- version
- effective_date
- document_id

Metadata filtering must happen before or during retrieval where supported.

Do not retrieve irrelevant regions and then rely entirely on the LLM to ignore them.

## 10. Query Normalization

Implement only low-risk normalization:

- trim whitespace
- normalize case where appropriate
- normalize known policy-code formatting
- extract obvious exact identifiers

Do not silently rewrite business meaning.

If an LLM rewrites a query, preserve the original query in traces and evaluation.

## 11. Evaluation Plan

Use the Phase-4 dataset and expand it with retrieval-specific cases.

Required comparison matrix:

1. Vector only
2. Lexical only
3. Hybrid
4. Hybrid + reranking
5. Adaptive routing

Measure at least:

- Hit Rate
- Recall@K
- MRR
- Context Precision
- Context Recall
- Faithfulness
- latency
- cost/query

Do not declare Hybrid or Reranking better unless the dataset shows improvement.

## 12. Required Evaluation Categories

Add cases containing:

- exact policy codes
- country + allowance combination
- synonym-heavy natural-language questions
- ambiguous policy terms
- older vs current policy version
- queries with no expected supporting policy

## 13. Observability

Add trace spans:

    retrieval.route
    retrieval.dense
    retrieval.lexical
    retrieval.fusion
    retrieval.rerank

Useful attributes:

- strategy
- dense result count
- lexical result count
- fused candidate count
- rerank candidate count
- final context count
- latency by stage

Do not log full confidential chunk text by default.

## 14. Example Strategy Contract

~~~python
class RetrievalStrategy(str, Enum):
    NO_RETRIEVAL = "NO_RETRIEVAL"
    DENSE = "DENSE"
    LEXICAL = "LEXICAL"
    HYBRID = "HYBRID"


class RetrievalDecision(BaseModel):
    strategy: RetrievalStrategy
    reason_code: str
~~~

## 15. Tests

Required:

- policy-code query selects LEXICAL or HYBRID
- natural-language semantic query can select DENSE
- mixed query selects HYBRID
- fusion removes duplicate chunks
- current policy version wins where business filtering requires it
- reranker returns only candidates it received
- no-retrieval route does not call vector or lexical search
- timeout in reranker degrades safely to fused ranking if that is the selected fallback policy

## 16. Acceptance Criteria

AC-01. Dense and lexical retrieval are independently executable.

AC-02. Hybrid fusion uses stable chunk identifiers.

AC-03. Reranking is a distinct, observable stage.

AC-04. Adaptive routing chooses from a fixed strategy enum.

AC-05. Comparison reports show quality, latency, and cost trade-offs.

AC-06. The chosen default retrieval strategy is justified by measured results.

AC-07. Metadata constraints can be applied without relying on generation-time instructions.

AC-08. Existing Agent tools do not need to know which internal retrieval strategy was used.

## 17. Explicitly Out of Scope

Do not add:

- GraphRAG
- knowledge graphs
- multi-agent search
- web search
- multimodal receipt parsing
- MCP
- autonomous prompt optimization
- model fine-tuning

## 18. Definition of Done

Phase 6 is complete when the team can answer:

> Which retrieval strategy is best for this class of expense-policy question, and what measured evidence supports that choice?

The output is not merely more retrieval components. It is a retrieval system whose strategy is explicit, measurable, and replaceable.

## Front-end Specification

### Goal

Keep the normal assistant UX stable while making retrieval strategy changes observable to learners.

### User-facing behavior

The main assistant should not require the user to choose DENSE, LEXICAL, or HYBRID manually.

The system chooses the strategy.

### Development-only retrieval panel

Behind a feature flag, show structured diagnostics such as:

- selected strategy
- router reason_code
- dense candidate count
- lexical candidate count
- fusion method
- reranked result count
- final citation order
- safe retrieval/reranking scores when exposed

Do not display raw embeddings.

Do not expose implementation details as a production requirement.

### Front-end acceptance criteria

FE-01. Existing assistant flows continue to work without user selection of retrieval strategy.

FE-02. A learner can inspect which strategy was selected for a request.

FE-03. Exact-term and hybrid examples can be demonstrated from the browser.

FE-04. Debug metadata is disabled by default for production users.

