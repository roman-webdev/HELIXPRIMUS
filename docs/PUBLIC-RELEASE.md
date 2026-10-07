# Public showcase preparation — 7 October 2026

HELIXPRIMUS — AI Customer Operations Platform. Portfolio Release Candidate / demo-grade, not production-ready.

Final local checks: backend 22/22 passed; frontend 18/18 passed; TypeScript/Vite build passed. Fresh SQLite migration and seed passed; m3_operations is head; Alembic check found no new operations; pip check passed. No new PostgreSQL credentials were used; backend/schema and migrations were not modified in this release preparation.

Synthetic data and policies, deterministic mock AI, uncalibrated rule scores, human approval gate and mock delivery only. No customer contact, real AI API, auth/multitenancy, billing or production-readiness claim. No WCAG compliance claim.

Deployment plan: free Render, one worker, ephemeral SQLite seeded at startup; Vercel frontend with same-origin API rewrites after the actual backend URL exists. Demo edits are shared and disposable, with no persistence guarantee. Cold starts and free-tier quotas remain.

GitHub push, live deployment and live acceptance have not yet been verified. No version tag or formal GitHub Release is required.
