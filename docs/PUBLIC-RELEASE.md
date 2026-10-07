# Public showcase preparation — 7 October 2026

HELIXPRIMUS — AI Customer Operations Platform. Portfolio Release Candidate / demo-grade, not production-ready.

Final local checks: backend 22/22 passed; frontend 18/18 passed; TypeScript/Vite build passed. Fresh SQLite migration and seed passed; m3_operations is head; Alembic check found no new operations; pip check passed. No new PostgreSQL credentials were used; backend/schema and migrations were not modified in this release preparation.

Synthetic data and policies, deterministic mock AI, uncalibrated rule scores, human approval gate and mock delivery only. No customer contact, real AI API, auth/multitenancy, billing or production-readiness claim. No WCAG compliance claim.

Deployment plan: free Render, one worker, ephemeral SQLite seeded at startup; Vercel frontend with same-origin API rewrites after the actual backend URL exists. Demo edits are shared and disposable, with no persistence guarantee. Cold starts and free-tier quotas remain.

## Published and verified

- Public source: https://github.com/roman-webdev/HELIXPRIMUS. Initial public commit `8095c6ca16c0e881df8aeb55b1f3aabeeac8830c`; Vercel rewrite configuration `68d7786`.
- Backend: https://helixprimus-api.onrender.com/health. Render Free deploy succeeded from `8095c6c`. Live health reports `ai_provider=mock`; synthetic Inbox and billing #5841 analysis → edit → approve → mock-send passed, including persisted synthetic message. Backend/schema files are identical to the initial release commit.
- Portfolio: https://roman-webdev.vercel.app/ — card and accepted screenshot published immediately before AstraSynq. Existing remote AstraSynq changes were merged without rewriting history. Published portfolio commit `4672d369ef502b2dca13d7f60d5b57c2347d1b82`; JavaScript syntax, diff checks, translated card and live screenshot loading passed. Static portfolio has no package build step.
- Preflight: only `.env.example` is included; it contains a non-secret SQLite example. Local DB, QA work, environments, caches, dependencies and build output are ignored. All eight screenshots were inspected and contain synthetic UI records. Current tracked source and full new Git history were checked for credential token patterns, private keys, credentialed PostgreSQL URLs and machine-specific paths; none were found. This is a release preflight, not a security certification.

## Pending

Vercel GitHub App initially had access only to portfolio. GitHub login was confirmed by the user; the selection of portfolio + HELIXPRIMUS was prepared and awaits the user's Save. Frontend deployment and live frontend/onboarding/EN-RU-UA acceptance are pending; no full live app URL is claimed. Vercel config already points same-origin `/api` and `/health` rewrites at the actual Render backend.

No version tag or formal GitHub Release was created.
