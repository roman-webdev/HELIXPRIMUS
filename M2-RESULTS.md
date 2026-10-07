# M2 local validation

Implemented: six scoped synthetic conversations, four deterministic scenarios and policies, inbox filters/message search, persisted status/priority/assignee/timestamps, human reply lifecycle, linked knowledge review, full-database Dashboard, filtered Audit, responsive light UI, scoped seed/reset and migration.

Validation: backend 17 passed; frontend 4 passed; TypeScript + production build PASS; pip check clean; Alembic m2_workspace (head), no drift; preview HTTP 200; proxied live Dashboard 6 total / 4 open / 2 resolved, priorities Medium 3 / High 3, intents billing 1 / delivery 2 / access 2 / cancellation 1, average resolution 120 minutes, mock sends 0 after reset.

Database backup before the scoped demo reset: work/pre-m2-demo-reset.db. Existing policies and unrelated conversation data are preserved. M1 endpoints remain compatible.

Limits: no live PostgreSQL validation; component tests mock the API; browser visual QA unavailable due sandbox ACL initialization failure. Vite dev scanning encountered sandbox directory-read restrictions; build and preview work. Inbox loads 50 records, Audit 100 matches; Dashboard is untruncated but intended for small local datasets. No auth or multi-operator concurrency guarantees. Rule matching has explicit precedence and limited language coverage.

No external AI, integrations, GitHub push or deploy performed. See README.md for setup, run, reset and demo flows.
