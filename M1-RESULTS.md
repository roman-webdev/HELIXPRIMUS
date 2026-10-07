# M1 backend + frontend validation

- React + TypeScript + Vite frontend: Inbox, Conversation, AI Analysis, Knowledge Base, Dashboard, Audit.
- Billing demo #5841: deterministic mock analysis with requested fields and Refund Policy §3.2.
- Browser flow verified against built frontend: load demo, analyze, edit, save, approve, Mock Send, Audit, reload persistence, Knowledge Base, Dashboard.
- Frontend build: PASS (`pnpm run build`), TypeScript strict checking included.
- Backend tests: 10 passed; one existing Starlette/httpx deprecation warning.
- Alembic check: no new upgrade operations detected. No schema migration required.
- Local preview: http://127.0.0.1:5173; FastAPI: http://127.0.0.1:8000.
- Codex sandbox blocks esbuild dependency optimization in dev mode through ancestor-directory read restrictions. Built preview is working and verified. Use `pnpm build` + `pnpm preview` in this environment.
- PostgreSQL server was not exercised. This remains a local synthetic M1 demo.
- No real AI/integrations, GitHub push, or deployment.
