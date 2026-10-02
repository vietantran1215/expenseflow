# Phase 7 — Multimodal RAG for Expense Receipts

## 1. Purpose

Add one new business capability that naturally requires multimodal AI:

> An employee can attach a receipt to an expense claim and ask the AI Service whether the receipt appears consistent with the relevant expense policy.

This phase remains entirely inside the Expense Reimbursement domain.

Primary learning outcome:

> Process images and scanned/PDF receipts, extract structured facts, combine those facts with policy retrieval, and generate an evidence-backed explanation without turning the project into a generic computer-vision platform.

## 2. Business Scope

Supported receipt types:

- hotel receipt
- meal receipt
- taxi/transport receipt
- flight or travel invoice
- simple scanned PDF receipt

The AI may:

- extract merchant
- extract date
- extract amount
- extract currency
- infer a limited expense category
- retrieve relevant policy
- explain likely compliance issues

The AI must not:

- approve a claim
- reimburse a claim
- treat extracted values as automatically correct
- overwrite claim financial values without explicit application logic

## 3. Core API Delta

Introduce a Receipt entity.

Minimum fields:

- id
- claim_id
- uploaded_by
- file_name
- media_type
- object_storage_key
- checksum
- created_at
- processing_status

Suggested processing status:

- UPLOADED
- PROCESSING
- READY
- FAILED

Core API owns receipt metadata and authorization.

Binary data should live in object storage or an equivalent local-development abstraction rather than inside the relational row.

## 4. Receipt API

Minimum endpoints:

- POST /claims/{claim_id}/receipts
- GET /claims/{claim_id}/receipts
- GET /claims/{claim_id}/receipts/{receipt_id}

Authorization rules from Phase 2 apply.

Only users allowed to access the claim may access the receipt.

Do not use public permanent receipt URLs.

## 5. AI Service API

Add:

POST /ai/receipts/{receipt_id}/analyze

Optional question:

~~~json
{
  "question": "Can this hotel receipt be claimed under the Singapore policy?"
}
~~~

Response:

~~~json
{
  "extracted": {
    "merchant": "Example Hotel",
    "date": "2026-09-12",
    "amount": 430.00,
    "currency": "USD",
    "category": "HOTEL"
  },
  "assessment": "The receipt appears to be within ...",
  "confidence_notes": [
    "The tax line is partially unreadable."
  ],
  "citations": [
    {
      "document_id": "singapore-travel-policy",
      "version": "2026.1",
      "chunk_id": "..."
    }
  ]
}
~~~

## 6. Multimodal Pipeline

Required flow:

    Receipt file
       |
       v
    Authorized file fetch
       |
       v
    File validation
       |
       v
    Multimodal extraction
       |
       v
    Structured receipt facts
       |
       +------------------+
       |                  |
       v                  v
    Policy query      Evidence metadata
       |
       v
    Adaptive/Hybrid Retrieval
       |
       v
    Relevant policy context
       |
       v
    Grounded assessment
       |
       v
    Answer + extraction + citations

## 7. Input Validation

Accept only explicitly supported media types.

At minimum validate:

- file size
- media type
- extension consistency where practical
- magic bytes/content signature where practical
- checksum
- page count for PDFs
- image dimensions if relevant

Reject unsupported or oversized files before expensive model calls.

Do not trust client-provided MIME type alone.

## 8. Structured Extraction

Define a strict schema.

~~~python
class ReceiptExtraction(BaseModel):
    merchant: str | None
    date: date | None
    amount: Decimal | None
    currency: str | None
    category: ExpenseCategory | None
    extraction_warnings: list[str]
~~~

The multimodal model output must be validated against this schema.

Unknown fields must not become business state automatically.

## 9. Confidence and Uncertainty

The system must surface uncertainty.

Examples:

- unreadable total
- multiple currencies shown
- date ambiguous
- category uncertain
- duplicate totals on the page

Do not convert "model returned a value" into "value is correct."

If required fields are uncertain, the response should request human verification.

## 10. Policy Grounding

Receipt analysis alone is not enough.

For a hotel receipt, the AI should construct a policy query using extracted facts, for example:

    category = HOTEL
    region = SINGAPORE
    amount = 430 USD

Then retrieve the applicable policy using the Phase-6 retrieval pipeline.

The final answer must distinguish:

- extracted receipt facts
- retrieved policy facts
- AI assessment

## 11. Scanned Policy Documents

As a secondary learning case, allow ingestion of scanned PDF policy documents.

Requirements:

- extract textual representation
- preserve page number
- preserve document metadata
- create retrievable chunks
- citations include page where available

Do not build a full document-layout research system.

## 12. Observability

Add spans:

- receipt.fetch
- receipt.validate
- multimodal.extract
- policy.retrieve
- multimodal.assess

Track:

- file type
- file size bucket
- extraction latency
- model tokens/cost
- extraction failure count
- required-field missing rate

Do not log raw receipt image bytes.

## 13. Evaluation Dataset

Create a small labeled multimodal dataset.

Suggested 20–30 examples:

- clear hotel receipts
- low-resolution receipts
- multiple totals
- different currencies
- scanned PDFs
- irrelevant image
- missing amount
- unsupported file

Labels should include expected extracted values where known and expected policy documents.

Metrics may include:

- exact-match or normalized accuracy for amount/currency/date
- category accuracy
- policy retrieval Recall@K
- groundedness/Faithfulness of final assessment
- extraction failure rate

## 14. Tests

Required:

- authorized employee can analyze own receipt
- unauthorized employee cannot fetch another employee's receipt
- unsupported file type is rejected
- oversized file is rejected
- extraction output is schema-validated
- ambiguous receipt produces warnings
- final policy assessment includes citations
- model failure does not corrupt claim state
- raw receipt data is not exposed in logs

## 15. Acceptance Criteria

AC-01. A receipt can be securely attached to an existing claim.

AC-02. AI Service can process at least image and PDF receipt inputs.

AC-03. Extracted values conform to a strict schema.

AC-04. Uncertain extraction is represented explicitly.

AC-05. Relevant expense policy is retrieved from the existing RAG system.

AC-06. Final answer distinguishes extracted facts from policy facts.

AC-07. Final policy claims include real citations.

AC-08. Receipt access is controlled by the same claim authorization boundary as the Core API.

AC-09. Multimodal processing is traced and measurable.

## 16. Explicitly Out of Scope

Do not add:

- generic image search
- facial recognition
- object detection platform
- invoice accounting integration
- automatic payment
- fraud-detection model training
- handwriting research
- video processing
- audio processing
- arbitrary user document ingestion into the policy corpus

## 17. Definition of Done

Phase 7 is complete when ExpenseFlow can take a real receipt artifact, extract useful structured facts, retrieve the applicable policy, and produce an evidence-backed explanation while preserving uncertainty and authorization boundaries.

## Front-end Specification

### Goal

Add receipt upload and multimodal-analysis UX while preserving the distinction between extracted AI data and authoritative claim data.

### Required claim-detail UI

- receipt list
- attach-receipt action
- upload progress
- processing status
- safe image/PDF preview when supported
- analyze-receipt action

### Required analysis UI

Display separately:

1. extracted receipt facts
2. extraction warnings/uncertainty
3. retrieved policy evidence
4. AI policy assessment

Never visually merge extracted values into authoritative claim values without a user-controlled application action.

### Client pre-checks

For early feedback the browser may check:

- selected file size
- selected MIME/extension
- obvious unsupported type

Backend validation remains authoritative.

### Front-end acceptance criteria

FE-01. An authorized employee can upload a supported receipt from claim detail.

FE-02. Processing status survives page refresh because it comes from the backend.

FE-03. Ambiguous extracted fields are visibly marked as uncertain.

FE-04. Policy citations are inspectable.

FE-05. An unauthorized receipt response is handled as an authorization error, not hidden by frontend logic.

