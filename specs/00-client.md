# ExpenseFlow — Web Client Specification

## 1. Purpose

This document defines the browser client architecture for ExpenseFlow across all ten phases.

The client exists to make each backend, RAG, agent, MCP, and security phase directly usable without turning the project into a separate frontend curriculum.

The web application is responsible for:

- presentation and navigation
- user input and form validation for user experience
- browser-session bootstrap
- typed HTTP calls to Auth, Core, and AI APIs
- AI streaming UX when introduced
- receipt upload and preview
- evidence and citation presentation
- explicit confirmation for consequential agent actions
- safe rendering of untrusted AI output
- client-side observability and correlation IDs

The client is not responsible for:

- expense business rules
- authorization decisions
- password policy enforcement
- claim-state enforcement
- RAG retrieval policy
- agent runtime policy
- MCP authorization
- security decisions that backend services must enforce

Backend APIs remain authoritative.

## 2. Front-end Technology Decision

Use a React + TypeScript single-page application with a Rust-based build and quality toolchain.

Baseline:

    React 19.x
    TypeScript
    Rsbuild 2.x
    Rspack 2.x
    React Router 7.x — Data Mode
    pnpm
    Node.js 24 LTS

Rust-based tooling:

- Rspack is the bundler used by Rsbuild.
- Rspack uses Rust for its core build pipeline.
- Rsbuild provides the project-level configuration and development experience.
- Rspack's built-in SWC pipeline handles JSX/TSX transformation.
- Biome is the default formatter and linter.
- React Compiler may use the Rust implementation supported by the Rspack/Rsbuild toolchain after compatibility tests pass.

Do not add Vite, Webpack, Babel, ESLint, or Prettier by default unless a concrete compatibility requirement appears.

Exact versions are pinned in the frontend lockfile.

## 3. Why a Static React SPA

ExpenseFlow does not need server-side rendering for its product goals.

The supported browser topology is:

    Browser
      |
      | same-origin HTTPS
      v
    Static React Application
      |
      | /api/*
      v
    Reverse Proxy / API Entry
      |
      +--> Auth Service
      +--> Core API
      +--> AI Service

Local development uses the Rsbuild development-server proxy to preserve the same path model.

Production may serve the generated static assets from:

- the same reverse proxy
- object storage + CDN
- another static hosting platform

The frontend must not depend on a Node.js server at runtime after build.

## 4. Same-Origin API Contract

Browser-visible paths should stay stable:

    /api/auth/*
    /api/core/*
    /api/ai/*

Internal service addresses remain deployment configuration.

Example:

    Browser
      |
      | GET /api/core/claims
      v
    API Entry / Reverse Proxy
      |
      v
    Core API

The proxy performs routing, TLS termination, and infrastructure concerns only.

It must not reimplement application business rules.

## 5. Browser Authentication Model

Phase 1 has no authentication.

From Phase 2 onward:

- access token is held in memory only
- refresh token is stored only in a Secure, HttpOnly, SameSite cookie
- refresh token is never exposed to React code
- localStorage, sessionStorage, and IndexedDB must not contain bearer or refresh tokens
- application reload may bootstrap a new access token using the refresh endpoint
- refresh/logout endpoints that depend on cookies require CSRF/origin protections
- Core and AI calls use the in-memory access token in the Authorization header
- a 401 may trigger at most one coordinated refresh attempt before returning the user to login

The frontend never decides whether a user is authorized.

Role-aware UI is convenience only.

## 6. Recommended Project Structure

    apps/web/
    ├── src/
    │   ├── app/
    │   │   ├── router.tsx
    │   │   ├── providers.tsx
    │   │   └── bootstrap.ts
    │   │
    │   ├── features/
    │   │   ├── auth/
    │   │   ├── claims/
    │   │   ├── assistant/
    │   │   ├── receipts/
    │   │   └── diagnostics/
    │   │
    │   ├── shared/
    │   │   ├── api/
    │   │   ├── components/
    │   │   ├── errors/
    │   │   └── utils/
    │   │
    │   ├── generated/
    │   ├── main.tsx
    │   └── styles.css
    │
    ├── public/
    ├── index.html
    ├── rsbuild.config.ts
    ├── biome.json
    ├── tsconfig.json
    └── package.json

Do not create empty future-phase feature folders before the phase introduces them.

## 7. Rsbuild Configuration

Minimal baseline:

~~~ts
// apps/web/rsbuild.config.ts
import { defineConfig } from "@rsbuild/core";
import { pluginReact } from "@rsbuild/plugin-react";

export default defineConfig({
  plugins: [
    // Adds React/TSX integration and Fast Refresh.
    pluginReact(),
  ],

  server: {
    proxy: {
      // Keep browser API paths stable while backend services
      // continue to run on separate local ports.
      "/api/core": "http://localhost:8000",
      "/api/auth": "http://localhost:8001",
      "/api/ai": "http://localhost:8002",
    },
  },
});
~~~

Proxy paths may be rewritten if backend routes do not include the service prefix.

The same external path contract should be reproduced by the production reverse proxy.

## 8. Routing

Use React Router 7 in Data Mode.

Phase routes are introduced only when needed.

Target route family:

    /
    /login
    /claims
    /claims/new
    /claims/:claimId
    /assistant
    /receipts/:receiptId
    /diagnostics

Protected-route behavior is a UX control.

Backend authorization remains mandatory.

## 9. Server State

Use TanStack Query for server state once the application has more than trivial CRUD.

Responsibilities:

- request lifecycle
- cache
- invalidation
- retry policy
- mutation state
- refetching

Do not use TanStack Query cache as authoritative business state.

Recommended query keys:

    ["claims", filters]
    ["claim", claimId]
    ["receipt", receiptId]
    ["policy-answer", requestId]

Write success must invalidate or update the minimum relevant cache entries.

## 10. Local UI State

Prefer in this order:

1. component state
2. reducer for complex local transitions
3. React context for small application-wide UI state

Do not introduce Redux, Zustand, MobX, or another global state library by default.

Add one only if real cross-feature state complexity justifies it.

## 11. API Contracts

Do not hand-maintain duplicate TypeScript representations of FastAPI schemas when OpenAPI is already authoritative.

Generate API types from the service OpenAPI documents.

Recommended:

    openapi-typescript
    openapi-fetch

Generated files live under:

    apps/web/src/generated/

Generated code must not contain handwritten business logic.

Example typed client:

~~~ts
// apps/web/src/shared/api/core-client.ts
import createClient from "openapi-fetch";
import type { paths } from "../../generated/core-api";

export const coreClient = createClient<paths>({
  // Same-origin path. Deployment topology stays outside React code.
  baseUrl: "/api/core",
});
~~~

## 12. Error Model

The frontend should normalize backend errors into one UI-safe shape.

Example:

~~~ts
export type ApiError = {
  code: string;
  message: string;
  requestId?: string;
  fieldErrors?: Record<string, string[]>;
};
~~~

Do not show:

- stack traces
- SQL errors
- internal exception classes
- tokens
- prompts
- internal model context

A request ID may be displayed to support debugging.

## 13. Forms

Use native HTML validation where useful and schema validation for complex forms.

Recommended:

- React Hook Form
- Zod when a client-side schema adds value

Client validation improves feedback.

It does not replace Pydantic/backend validation.

Financial calculations such as claim total remain server-authoritative.

## 14. AI Output Rendering

Treat every LLM output as untrusted content.

Rules:

- render text as text by default
- sanitize Markdown rendering
- raw HTML is disabled
- do not execute model-generated JavaScript
- do not convert model text into hidden browser commands
- external links require safe protocol validation
- citations are rendered from structured citation objects, not parsed from arbitrary prose
- model-generated tool/action descriptions do not execute automatically

## 15. Streaming

Streaming is introduced only when the AI phase benefits from it.

Preferred flow:

    Browser
      |
      | fetch/SSE request
      v
    /api/ai/assistant/stream
      |
      v
    AI Service

The browser must support:

- AbortController cancellation
- reconnect only when safe
- explicit completed/error state
- incremental text rendering
- structured events for citations and tool activity

Do not retry write/tool streams automatically.

## 16. Receipt UX

From Phase 7:

- client-side file size/type pre-check for early feedback
- backend remains authoritative validator
- upload progress
- preview when safe
- processing state
- extracted fields shown separately from claim-authoritative fields
- uncertain fields visually identified
- user verification before copying extracted data into a claim

## 17. Consequential Agent Actions

From Phase 8 onward, an AI response may propose a business action.

The frontend must separate:

    model proposal
        !=
    executable action

For a consequential action such as submit:

1. receive structured proposed action
2. display exact target and effect
3. request explicit user confirmation
4. send the confirmation to trusted backend runtime
5. backend re-authorizes
6. execute
7. display authoritative result

Never infer confirmation from unrelated chat text.

## 18. Front-end Security

Required throughout applicable phases:

- no secrets in source or generated bundle
- no bearer/refresh token in persistent browser storage
- safe Markdown/HTML handling
- CSP-compatible implementation
- no model-generated script execution
- no arbitrary URL navigation from model output
- no sensitive values in analytics
- no authorization decisions based only on hidden/disabled UI controls
- dependency lockfile committed
- dependency/security scanning in CI

## 19. Accessibility

Minimum baseline:

- semantic HTML
- keyboard-accessible forms and dialogs
- visible focus
- labels for form inputs
- accessible validation errors
- no color-only status meaning
- confirmation dialogs trap and restore focus correctly
- streaming answer updates do not continuously disrupt screen readers

## 20. Observability

Client requests should propagate or surface correlation IDs where supported.

Track browser-safe telemetry such as:

- route
- request duration
- request failure code
- frontend exception
- stream cancellation
- upload failure
- confirmation accepted/cancelled

Do not capture:

- passwords
- access tokens
- refresh tokens
- receipt bytes
- full AI prompts
- sensitive claim data by default

## 21. Testing Strategy

Component tests:

    Vitest
    React Testing Library

End-to-end tests:

    Playwright

Quality checks:

    TypeScript strict typecheck
    Biome check
    production build

Minimum CI:

    pnpm install --frozen-lockfile
    pnpm typecheck
    pnpm check
    pnpm test
    pnpm build

Run Playwright for the phase-critical browser flows.

## 22. Phase Evolution

| Phase | Front-end Capability Added |
|---|---|
| 1 | Minimal React shell, claim list/create/detail/edit and workflow actions |
| 2 | Login/session bootstrap, role-aware UX, protected routes, auth failure handling |
| 3 | Policy Q&A page with structured citations |
| 4 | Request/trace diagnostics and quality metadata for development |
| 5 | Unified agent assistant, streaming, tool/evidence activity |
| 6 | Retrieval strategy and reranking diagnostics behind a development flag |
| 7 | Receipt upload, preview, extraction, uncertainty and policy assessment |
| 8 | MCP-backed agent actions, draft creation and explicit submit confirmation |
| 9 | LLM-output rendering hardening and browser security regression tests |
| 10 | Agent-action policy UX, confirmation integrity, denial/termination states |

Each phase-specific document defines the exact UI scope and acceptance criteria.

## 23. Front-end Non-Goals

Do not add unless a later requirement justifies them:

- SSR
- React Server Components
- a Node.js production BFF
- micro-frontends
- Redux
- design-system monorepo
- WebSockets when SSE/fetch streaming is sufficient
- offline-first synchronization
- PWA behavior
- real-time collaborative editing
- generic admin portal
- generic workflow builder

## 24. Definition of Done

The client architecture is correctly followed when:

- the production frontend is a statically buildable React application
- Rsbuild/Rspack is the supported build path
- TypeScript runs in strict mode
- browser-facing API paths are deployment-stable
- frontend code does not duplicate backend business or authorization rules
- authentication tokens follow the memory + HttpOnly refresh-cookie model
- generated API contracts reduce schema drift
- AI output is rendered as untrusted content
- consequential agent actions require explicit confirmation
- every phase introduces only the minimum UI needed to demonstrate that phase
