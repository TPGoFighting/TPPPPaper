# TPaper — Agent Guide

AI exam paper converter: PDF / scanned PDF / DOCX / images → interactive HTML review pages.
Stack: FastAPI + SQLAlchemy + Celery/Redis + Next.js 14 + Docker Compose. Single-admin, self-hosted, BYOK.

## Quick Start

```bash
make dev          # full stack via Docker Compose
make dev-api      # backend only (hot-reload, port 8000)
make dev-worker   # Celery worker only
make dev-web      # Next.js frontend (port 3000)
make test         # all tests
make lint         # ruff + next lint
make check-docs   # documentation freshness check
pre-commit install  # enable pre-commit hooks
```

## Project Structure

```
backend/app/          FastAPI backend
  api/                Routes: auth, papers, uploads, jobs, drafts, publications, public, assets, model_profiles, metrics
  models/             SQLAlchemy ORM (Paper, SourceFile, ProcessingJob, PaperDraft, PublicationVersion, Asset, ModelProfile)
  schemas.py          Pydantic schemas + PaperDocument validator
  adapters/           OpenAI-compatible + Anthropic model adapters (with structured model call logging)
  repositories/       Data access layer
  security/           bcrypt, Fernet encryption, SSRF guard, HTML/CSS sanitizer (with sanitize event logging)
  storage/            Local filesystem storage
  prompts/            Versioned LLM prompts with XML data fencing (extract_v1, generate_v1, answering_v1, presentation_v1, simple_v1)
  logging_config.py   Structured logging (structlog) — JSON for production, console for dev
worker/               Celery async tasks
  tasks.py            ACTIVE — full pipeline (preprocess → extract → generate → render → sanitize)
  tasks_simple.py     ACTIVE — simplified pipeline (fast path, single LLM call + answering)
  pipeline/           Preprocessing, extraction, generation, rendering, sanitization stages
web/src/              Next.js 14 frontend
  app/admin/          Admin dashboard, upload, settings, paper detail
  app/p/[slug]/       Public review page (no auth required)
  components/         Shared UI components
  lib/api.ts          API client with retry + CSRF
docs/                 Architecture docs, file reference, changelogs
docker/               Dockerfiles (api, worker, web)
tests/                Test suite
  unit/               Unit tests (security, schema, architecture, prompt injection — 166 tests)
  conftest.py         Shared fixtures (test DB, test client, auth helpers)
scripts/              Agent tool scripts
  verify_paper.py     Validate PaperDocument JSON
  sanitize_test.py    Test HTML/CSS sanitizer interactively
  render_preview.py   Render PaperDocument to HTML preview
  check_docs.py       Documentation freshness checker (broken links, stale refs, secrets)
.github/workflows/    CI pipeline (lint → test → build → doc-check → docker)
.pre-commit-config.yaml  Pre-commit hooks (ruff, yaml/json, secret detection)
web/.eslintrc.json    ESLint config (next/core-web-vitals + typescript-eslint)
SPEC.md               Product specification — the ultimate authority
pyproject.toml        Root pytest config (pythonpath=backend)
```

## Architecture Constraints

- Dependency direction: `api → repositories → models`. API layer must NOT import `storage` or `processing` directly.
- Models generate HTML/CSS only — **never JavaScript**. Runtime handles answering/scoring.
- All AI output MUST pass through sanitization before saving or publishing.
- Public pages enforce strict CSP: `script-src 'none'`.
- Static logic (validators, runtime, components) lives in code; models cannot modify it.

## Security Red Lines

- NEVER hardcode API keys, passwords, or secrets in source code.
- Treat ALL user-uploaded content as untrusted input.
- SSRF protection blocks loopback, private, link-local, and cloud metadata IPs by default.
- HTML sanitizer forbids: event attributes (`on*=` on non-button elements), `<iframe>`, `javascript:` URLs, `<object>`, `<embed>`, `<form>`. Note: `<script>` is intentionally allowed for the interactive runtime.
- CSS sanitizer forbids: remote `@import`, `javascript:` in `url()`, page-covering `position: fixed`.
- API keys use Fernet envelope encryption; master secret from env var.
- Source files auto-expire after 7 days.
- Login endpoint has rate limiting (10 req/min per IP) to prevent brute-force attacks.
- All state-changing endpoints require CSRF protection (double-submit cookie token with `X-Requested-With` fallback).
- File uploads validate magic bytes against declared MIME type to prevent type spoofing.
- Upload size limit enforced on both declared size and actual bytes received.

## Security Checklist

Run `make security-test` to verify all security tests pass (rate limiting, CSRF, upload validation, file type detection, sanitization, prompt injection — 170+ tests).

Run `make audit` to scan Python and npm dependencies for known vulnerabilities.

- `make security-test` — security, hardening, and prompt injection tests
- `make audit` — dependency vulnerability scan (pip-audit + npm audit)
- `make sanitize-test` — interactive HTML/CSS sanitizer testing
- Pre-commit hooks include secret detection (detect-private-key)

## Code Conventions

- Python: Ruff linter, line-length 100, Python 3.11+. Format with `ruff format`.
- TypeScript: Tailwind CSS, Next.js 14 App Router. Run `cd web && npm run lint` before commit.
- DB migrations via Alembic: `make migrate-create MSG="description"`.
- Commit messages: conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).

## Testing

- Backend: `make test-backend` (pytest, 166 tests covering security, schema, architecture, prompt injection, security hardening)
- Sanitize tests MUST cover: event attributes, `javascript:` URLs, CSS `@import`, iframe injection. Note: `<script>` is intentionally in ALLOWED_TAGS for the interactive runtime.
- Schema tests MUST cover: missing fields, duplicate IDs, invalid `correct_keys` references, bad question types, section→question reference integrity.
- Architecture tests enforce dependency direction via AST scanning (api→repositories→models).
- Prompt injection tests verify: XML data fencing in all prompts, safety instructions in all system prompts, 11 injection payloads don't penetrate system instructions.
- E2E smoke test: `python tests/e2e_production_test.py` (requires running deployment).
- Agent scripts: `scripts/verify_paper.py` (validate JSON), `scripts/sanitize_test.py` (test sanitizer), `scripts/render_preview.py` (render HTML preview).

## Observability

- Structured logging via `structlog`. Set `LOG_FORMAT=json` for production JSON, default is colored console.
- Model calls are logged at `model_call` event with model, latency, token usage, success/failure.
- Sanitization blocks are logged at `sanitize_blocked` event with sanitizer type, blocked items, input/output sizes.
- HTTP requests are logged at `api_request` event with method, path, status, duration, request ID.
- Dashboard metrics at `GET /api/metrics/dashboard`: paper status distribution, job success rate, processing time percentiles, file type distribution, 24h/7d activity summary.

## Common Pitfalls

- `worker/archive/tasks_v2.py`, `worker/archive/extract_v2.py`, `worker/archive/preprocess_v2.py` — NOT registered in Celery, do not use.
- `backend/app/processing.py` is a dev-only in-process fallback when Redis is unavailable, not the main path.
- Public page `/p/{slug}` requires NO auth; all admin endpoints require session cookie + CSRF header.
- `SPEC.md` is the ultimate authority. If code disagrees with SPEC, fix the code.
- Docker exposes API on port 8086 (not 8000) in production compose.
- When modifying prompts, update the version in `backend/app/prompts/` and add a CHANGELOG entry. Each prompt module has a `VERSION` constant.
- CI runs automatically on push/PR: lint → test → build → doc-check → docker. Fix lint issues before pushing.
- Pre-commit hooks run on `git commit`: ruff, yaml/json checks, secret detection. Install with `pre-commit install`.
- Run `make check-docs` periodically to detect broken file references and stale docs.
- Known vulnerability: `ecdsa` 0.19.2 (PYSEC-2026-1325) — used by `python-jose`, no fix available yet. Next.js 14 has 4 high-severity CVEs requiring upgrade to v16 (breaking change, separate task).

## Worker Architecture

Two active task pipelines registered in Celery:

1. `worker.tasks.process_paper` — Full pipeline: preprocess → extract (map-reduce, parallel LLM) → generate (chunked + merge) → render → sanitize
2. `worker.tasks_simple.process_paper_simple` — Fast pipeline: text extraction → single LLM call → template render → answering enrichment

Both route to queue `tpaper`. Choose based on document complexity.
