# UI language support

The globe selector in the top bar opens English, Русский and Українська. Switching updates the current screen without reloading or resetting filters, conversation selection or an unsaved reply. The choice is saved as `helixprimus.language` in localStorage and restored on reload. Missing or unsupported values fall back to English. If storage is unavailable, language switching still works for the current session.

Implementation: `frontend/src/i18n.tsx` and the matching Russian/Ukrainian dictionaries in `frontend/src/translations.json`. English source copy is the fallback. No additional package was installed. The document language and date/time formatting follow the selected language. The native select supports keyboard, touch and screen readers.

Coverage: navigation, headers, Dashboard and metric definitions, Inbox, conversation controls, analysis labels/summaries/rule explanations, Knowledge Base interface and all four synthetic policy sources, Audit/Timeline event labels, filters, SLA, reply actions, notices, loading/empty/error states and demo guidance. Known backend errors are translated; unrecognized errors show a localized request-failure message.

Customer messages, editable suggested replies, operator-authored notes, synthetic conversation titles retain their source language. Quoted customer evidence and technical policy keys in explanations remain verbatim. Status values, intent codes, event actions, identifiers and API payloads are unchanged; translation is a display concern. Backend models, migrations and product scope are unchanged.

Validation (2026-10-07):

- Frontend: 14 tests passed, including both translated languages, remount persistence, return to English, localized reply workflow, unchanged API values, retained unsaved draft, invalid saved language, blocked storage, storage synchronization and localized error recovery.
- Backend: 22 tests passed using a fresh workspace `--basetemp` (the default system pytest temp folder was inaccessible).
- Frontend production build: passed.
- Browser: Russian Inbox/conversation/analysis, Ukrainian Dashboard, reload persistence and existing demo content inspected locally.

No GitHub push or deployment performed.
