> Historical local RC report. The subsequent public showcase is authorized; current release verification is tracked in [PUBLIC-RELEASE.md](PUBLIC-RELEASE.md). PostgreSQL evidence below remains historical and has not been upgraded to a new claim.

# HELIXPRIMUS RC polish — 7 October 2026

Status: UI, practical accessibility, copy, documentation, SQLite regression and browser QA completed. Final RC sign-off is pending PostgreSQL migrations/smoke/head/drift through the existing safe environment configuration. This run has not verified PostgreSQL schema state. Prior M3 results are not substituted for current evidence.

Project: HELIXPRIMUS. Positioning remains **AI Customer Operations Platform**. No new product screens/features, external AI, integrations, push, public deployment, release or tag were added.

## Changes

- Preserved the green premium light workspace. Aligned Inbox filters, standardized M3 controls, increased small operational text, improved cards, headers, long text, badges and narrow viewport behavior.
- Replaced generic section subtitles and internal milestone wording with operational copy. Retained clear synthetic data, deterministic confidence and local Mock Send labels. Displayed readable intent names without changing stored values.
- Added skip navigation, active-page and selected-conversation semantics, heading hierarchy, table column scopes and accessible meter names. Extended visible focus to links, disclosure summaries and scrollable table regions.
- Mobile navigation now exposes expanded/controlled state, moves focus into the opened navigation, supports Escape, restores focus and has an explicit Close navigation button. Forms keep labels; notes and replies keep accessible names.
- Measured low contrast on inactive navigation (4.07:1), header secondary text (2.97:1) and deterministic-analysis label (3.22:1). Corrected and remeasured to 6.23:1, 6.05:1 and 5.64:1 respectively. This is a sampled practical check, not a complete contrast audit.
- Improved the actual backend-unavailable message and removed the review badge when no conversation is selected.
- Rewrote README around the problem, workflow, architecture/product decisions, provider boundary, M3 behavior, setup/run/reset/tests, SQLite/PostgreSQL, smoke safety and known limitations.

## Regression results

| Check | Result in this run |
| --- | --- |
| Backend | 22 tests passed |
| Frontend | 5 tests passed on final functional source |
| TypeScript / Vite build | PASS after final contrast styles |
| Python dependency compatibility | `pip check`: no broken requirements |
| Frontend dependencies | 13 direct packages present; frozen-lockfile offline install already up to date |
| SQLite | `m3_operations (head)`; Alembic check reports no new operations |
| PostgreSQL server | Existing private SCRAM instance restored; 127.0.0.1:55432 accepts connections |
| PostgreSQL schema / smoke | PENDING: no DATABASE_URL/PG credential environment is available in this session |
| Browser | Real local desktop and 390px QA; final built preview also inspected |

Dependency checks establish local compatibility and lock consistency, not a vulnerability certification. No dependencies were upgraded for polish. Backend/schema logic and migrations were unchanged.

## Screen / flow evidence

1. **Dashboard — healthy.** Cards, readable intent names, workload/backlog/SLA distributions and seven-day trend checked at desktop/390px. Refresh metrics works; all sampled meters have names. [Desktop](screenshots/01-dashboard.jpg) · [390px](screenshots/01-dashboard-390.jpg).
2. **Inbox — healthy.** Combined status/assignee/SLA filters return matching records; a no-match SLA and missing search phrase show empty results. Filter Tab order and visible focus checked. [Desktop](screenshots/02-inbox.jpg) · [390px](screenshots/02-inbox-390.jpg).
3. **Conversation — healthy.** Billing #5841 edited, saved, approved via keyboard and Mock Sent. Mock Send was disabled before approval and after send. Reassignment to Sam Lee, New → In review → Resolved → Reopen all persisted. [Conversation / analysis](screenshots/03-conversation-analysis.jpg).
4. **AI Analysis — healthy.** Fresh deterministic analysis exposes named confidence meters, honest uncalibrated-score copy, issue summary and policy link. “Why this analysis?” expands with Enter; desktop/390px explanations remain readable. It retains the established shared workspace layout.
5. **Knowledge Base — healthy.** All four synthetic policies inspected, long policy text reflows and no-match policy search works. [Desktop](screenshots/05-knowledge.jpg).
6. **Audit / Timeline — healthy within local scope.** Mock-send action filter shows the persisted response. Long internal note and status/assignment/send history survive reload. Mobile Audit intentionally uses a named, keyboard-focusable horizontal table region; the page itself does not overflow. [Audit](screenshots/04-audit.jpg) · [390px conversation/timeline evidence](screenshots/03-conversation-390.jpg).

Browser checks also covered a real stopped-backend error, keyboard Retry after restart, loaded-state recovery and an empty initial workspace during failure. Persistence was verified after reload on SQLite, then inspected again in the built preview. Synthetic QA changes remain in the local database; the existing dataset was not reset, so its SLAs have naturally aged. README explains how to get a fresh anchored M3 dataset.

Screenshots were captured in this run, saved and inspected before acceptance. Compact desktop showcase images are in `docs/screenshots`; mobile images supplement QA evidence. Initial files are backed up under `work/rc-before` for recovery.

## Accessibility limits

Checked actual keyboard activation/Tab navigation, focus visibility, mobile Escape/focus restoration, named forms/buttons/meters, heading structure and browser accessibility/DOM representations. No NVDA/JAWS listening session, exhaustive keyboard traversal of every state, full WCAG audit or certification was performed. The long mobile shared workspace still requires vertical scrolling; no new navigation screen or layout redesign was introduced.

## Readiness and remaining work

This is ready for local portfolio review. Unconditional RC closure and a future GitHub/public release decision remain pending the current PostgreSQL verification. Supply the location/loading method for the existing safe environment configuration; passwords need not be placed in chat or project files. Then run migrations from a fresh disposable `_smoke` database, the existing smoke, current/head and Alembic drift checks, and update this report with observed results.

Known product limits remain: no auth/concurrency or trusted author attribution; in-process analytics; uncalibrated deterministic confidence; synthetic data/policies; mock delivery; no real provider/integrations; no production-readiness or WCAG claim. Any future push/public deployment/release needs separate user authorization.
