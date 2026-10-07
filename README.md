# HELIXPRIMUS — AI Customer Operations Platform

HELIXPRIMUS is a **Portfolio Release Candidate / demo-grade prototype** for customer operations teams. It connects conversation triage, policy review, a suggested response, explicit human approval and an auditable operator workflow in one light B2B workspace.

The problem it explores: an operator needs to understand a customer issue, find the relevant policy, review a response and keep ownership and resolution history visible. The current M3 implementation uses synthetic conversations and a deterministic analysis provider. **Mock Send records a message locally; it does not contact a customer.** This is not production-ready.

## Core workflow

1. Open Inbox and search or filter by status, priority, assignee or active resolution SLA.
2. Select billing **#5841**, inspect the messages and run analysis. Review the issue summary, extracted entities, policy match, rule scores and explanations.
3. Review the linked synthetic policy. **Edit → Save edits → Approve → Mock Send**. Every edit invalidates approval; sending requires the exact approved text and rejects repeat sends.
4. Reassign the conversation, add an internal note and move **New → In review → Resolved**. Reopen returns to In review.
5. Inspect the conversation timeline, filtered Audit trail and Dashboard. Reload to verify persisted changes.

## Current M3 capabilities

- Six synthetic scenarios: duplicate billing, delivery delay, account lockout, cancellation, resolved delivery follow-up and resolved password reset. Four synthetic policy sources.
- DB-driven analytics: conversation totals, priority/intent/status breakdowns, workload, backlog, seven-day UTC volume, response/resolution averages, approval and mock-send rates with coverage definitions.
- Resolution SLA from creation: High 120 minutes, Medium 480, Low 1440. At risk begins at 80%; overdue begins after the deadline. Resolved conversations freeze the outcome and leave active counts/filter results. Reopen retains the original deadline; priority changes recalculate the target. Refresh/reload recalculates time-dependent values.
- Separate internal notes with a 5,000-character limit and demo author selection. Timeline/Audit include analysis, assignment, status, priority, edit, approval and delivery events.
- Local responsive interface with recoverable errors, loading/empty states and practical keyboard/accessibility improvements. No WCAG certification is claimed.

## Architecture / Product decisions

| Layer | Responsibility |
| --- | --- |
| React / TypeScript / Vite | Operator workspace; API calls through the local `/api` proxy |
| FastAPI | Validation and workflow endpoints; explicit error responses |
| SQLAlchemy / Alembic | Persisted conversations, messages, analyses, knowledge, audit and internal notes; versioned migrations |
| SQLite / PostgreSQL | Same application schema; SQLite is the default local setup |
| Provider abstraction | Structured analysis contract with provider/version and input digest; only `mock` is implemented |
| Operations calculations | Synchronous in-process analytics and derived SLA values from database records |

Human approval is a persisted workflow gate, not a cosmetic button state. Message creation and its audit event commit atomically. Internal notes remain separate from customer messages and analysis input. Alembic owns schema creation; runtime code does not call `create_all`.

The deterministic provider uses ordered keyword rules (billing, access, cancellation, delivery, then fallback), #number extraction and exact policy keys present in the database. It does not use semantic retrieval, RAG or an external model. Confidence scores are fixed rule estimates, **not calibrated probabilities**. They never authorize sending. Unsupported `AI_PROVIDER` values fail explicitly.

Analytics deliberately favor inspectability over scale. First response averages creation → earliest assistant message; resolution averages creation → latest resolution, excluding missing samples. Reopen clears resolution. Approval rate counts analyses ever approved / all analyses, including historical versions. Mock-send success includes recorded authorization/repeat-send rejections; historical M2 rejection history is unavailable. The UI exposes denominators and definitions.

## Setup — Windows / PowerShell

Prerequisites: Python 3.12, Node.js 22.12+ (previously validated with Node 24), pnpm 11. Run from the project root:

```powershell
cd HELIXPRIMUS
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
$env:DATABASE_URL = 'sqlite:///./helixprimus.db'
$env:AI_PROVIDER = 'mock'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.demo seed
pnpm --dir frontend install --frozen-lockfile
```

Python and frontend dependencies are pinned by their lock files. `.env.example` is a non-secret reference; neither the app nor Alembic loads `.env` automatically. Set environment variables in each backend terminal. SQLite paths are relative to the project root. Public source: https://github.com/roman-webdev/HELIXPRIMUS.

## Run

Backend, from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Second terminal:

```powershell
pnpm --dir frontend dev
```

Open `http://127.0.0.1:5173/`; API docs are at `http://127.0.0.1:8000/docs`. Bind to loopback because this prototype has no authentication. Both Vite dev and preview proxy `/api` and `/health` to port 8000.

For a built preview:

```powershell
pnpm --dir frontend build
pnpm --dir frontend preview
```

## Sample data / reset

```powershell
.\.venv\Scripts\python.exe -m app.demo seed
# Stop the backend before resetting; reload the frontend afterward.
.\.venv\Scripts\python.exe -m app.demo reset
```

Both commands migrate and populate data through the API in-process. Seed and **Load sample data** are idempotent and preserve existing edits/analyses. Reset recreates the six owned references in `app/dataset.py` and their messages, analyses, internal notes and conversation audit events. IDs change; interactive approvals/sends are cleared. Unrelated records and existing policy edits remain. Missing policies are restored.

Fresh M3 reset uses one current UTC minute anchor: billing is on track, delivery at risk, lockout overdue and cancellation on track. Two resolved records include clearly synthetic historical replies, approvals, sends and notes for analytics. Existing old datasets may have aged SLAs or older analyses; seed does not overwrite them. Run analysis to obtain current rule explanations, or use reset for a complete fresh demonstration.

## Tests / dependency / schema checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=work/pytest-run
.\.venv\Scripts\python.exe -m pip check
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend list --depth 0
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

`work/pytest-run` must contain only disposable test files: pytest clears it. Backend tests use isolated SQLite databases and real migrations; they cover reply authorization, provider failure, persistence, foreign keys, scoped reset, M3 operations and PostgreSQL DDL compilation. Frontend component tests use an in-memory API, including critical flows, remount persistence, filters, analytics, notes/timeline and error recovery. They are not browser E2E tests. Build includes TypeScript checking. Schema head is `m3_operations`.

`pip check` verifies installed Python dependency compatibility; the frontend dependency listing verifies installed direct packages. These are not vulnerability certifications. The existing jsdom dependency has a deprecated transitive `whatwg-encoding`; no major upgrade is introduced merely to suppress that notice.

## PostgreSQL smoke

Use the existing safe local environment configuration. Credentials belong in environment variables, never project files or `.env.example`. Use a separate disposable loopback PostgreSQL database whose name ends in `_smoke`; never the normal workspace database. After loading its `DATABASE_URL` and setting `AI_PROVIDER=mock`:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.postgres_smoke
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

The smoke refuses other database types, non-loopback hosts and names without `_smoke`. It migrates, resets/reseeds owned synthetic data, exercises actual PostgreSQL through FastAPI TestClient and verifies filters/search, policy matches, edit/approve/send gates, persistence, M3 notes/timeline, transitions, analytics and drift. It leaves synthetic results for inspection. To verify migrations from zero, provide a newly created disposable `_smoke` database through the same safe environment mechanism.

## API surface

`/api/v1/conversations` supports combined status, priority, assignee, `q`, active `sla_state`, limit and offset. Search covers title/message content and escapes literal `%`/`_`. Conversation detail supports messages, analyses, reply actions, status/priority/assignment updates, notes and timeline. `/api/v1/knowledge`, `/api/v1/dashboard`, `/api/v1/audit`, `/api/v1/operators` and `/api/v1/demo/m3` complete the workspace. The M2 seed alias remains compatible. See local Swagger for request schemas.

## Showcase / verification

Accepted screenshots are stored in `docs/screenshots/`. `docs/RC-QA.md` records this RC pass, regression evidence and remaining verification gaps. Screenshots show synthetic local records, not real customer activity.

## Known limitations

- No authentication, RBAC, multitenancy or trusted operator attribution. The demo author selector is not identity verification.
- No concurrency guarantees, version checks, concurrent operators or realtime collaboration.
- In-process analytics scan database records; no large-volume performance claims. Inbox loads up to 50 records; Audit/timeline up to 100; Dashboard reads all records.
- Uncalibrated deterministic confidence; no real AI provider, external integrations, semantic retrieval or RAG.
- Mock delivery and synthetic data/policies; no Telegram/email, refunds or other external actions.
- No Redis/Celery, pgvector, billing, production deployment or full accessibility certification.

## Public demo deployment

The public showcase is authorized; deployment verification is recorded in `docs/PUBLIC-RELEASE.md`. This remains demo-grade and is not production-ready.

Use the free Render blueprint in `render.yaml`. The backend runs one process with `AI_PROVIDER=mock` and an ephemeral SQLite database under `/tmp`. Startup migrates and seeds synthetic records. Data is shared between visitors and disappears on restart, redeploy or idle spin-down. Do not enter private or real customer data. Free services can cold-start and are subject to platform limits. No paid disk or managed database is required.

Deploy `frontend/` on Vercel using the existing lockfile, build command `pnpm build`, output `dist`. After Render assigns a real backend URL, configure Vercel rewrites for `/api/:path*` and `/health` to that URL before the SPA fallback. Browser requests stay on the frontend origin, so no wildcard CORS policy or browser credentials are needed. No real AI or delivery credentials are used.

PostgreSQL remains supported through SQLAlchemy/Alembic. The public demo uses SQLite; this release does not claim a new credentialed PostgreSQL verification. See the historical RC QA report for its verification limits.
