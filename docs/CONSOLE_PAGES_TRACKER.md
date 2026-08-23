# Console Pages Build Tracker — SUPERSEDED

**This standalone tracker has been folded into the canonical tracker.**

See **`docs/MIGRATION_TRACKER.md` → Phase 3.11 — Frontend Information
Architecture Redesign**. That section is now the single source of truth for
console-page build status (per `CLAUDE.md`, `MIGRATION_TRACKER.md` is *the*
tracker).

The 3.11 rewrite (2026-08-20) supersedes this file's earlier "M.x" numbering
with the repo's real 3.11.x scheme, corrects stale statuses (landing, login,
shell, `/command` already shipped), expands the 11 workflow pages into per-page
rows tagged by their actual data source (`[data-ready]` / `[needs-backend]` /
`[UI-only]`), and adds a **Backend prerequisites** table (BE-1…BE-6) for the
endpoints those pages need that don't exist yet — most importantly the two hard
blockers: `GET /incidents` (list) and `GET /audit`.

## 2026-08-24 — push log: console design-token namespacing + landing/login

Not a status table (see MIGRATION_TRACKER §3.11 for that) — just what shipped
in this push, per file, in §3.11 order.

| Item | File(s) | What shipped |
|---|---|---|
| 3.11.1 | `app/page.tsx`, `components/landing/*` (13 files) | Public landing page built out — hero, features, how-it-works, infrastructure, metrics, integrations, security, developers, testimonials, pricing, CTA, footer + nav. Replaces the old `redirect("/command")` stub. |
| 3.11.2 | `app/login/page.tsx` | New dedicated `/login` route (split-screen, per UX §3.1). |
| 3.11.3 | `app/layout.tsx`, `app/globals.css`, `components/Sidebar.tsx`, `components/ConsoleTopbar.tsx`, `lib/operations-context.tsx` | Renamed console spacing tokens (`--spacing-xs` → `--spacing-console-xs`, etc.) so they don't collide with the landing page's own scale; added Instrument Sans/Serif, JetBrains Mono, Oswald fonts; swapped the inline theme `<script>` for `next/script`; `operations-context` now fetches `GET /recommendations` on mount so a mid-incident refresh doesn't show an empty panel until the next WS push. |
| 3.11.4 | `components/Dashboard.tsx`, `components/DashboardGrid.tsx` | Console-token rename only — still the full dashboard per the existing 3.11.4 cockpit-trim caveat. |
| 3.11.6.1 | `components/AlertsPage.tsx` | Console-token rename. |
| 3.11.6.2 | `components/IncidentsListPage.tsx` | Console-token rename. |
| 3.11.6.3 | `components/IncidentDetailPage.tsx` | Console-token rename. |
| 3.11.6.4 | `components/RecommendationsPage.tsx`, `components/RecommendationsPanel.tsx` | Console-token rename. |
| 3.11.6.5 | `components/ResourcesPage.tsx`, `components/ResourcesPanel.tsx` | Console-token rename. |
| 3.11.6.6 | `components/RoutesPage.tsx`, `components/MapPage.tsx`, `components/LayersToggle.tsx` | Console-token rename; layer-toggle checkboxes now use `accent-console-primary`. |
| 3.11.6.7 | `components/MedicalPage.tsx` | Console-token rename. |
| 3.11.6.8 | `components/CitizensPage.tsx`, `components/CitizenInboxPanel.tsx` | Console-token rename. |
| 3.11.6.9 | `components/AgentsPage.tsx` | Console-token rename. |
| 3.11.6.10 | `components/AuditPage.tsx` | Console-token rename. |
| 3.11.6.11 | `components/SettingsPage.tsx`, `components/ThemeToggle.tsx` | Console-token rename. |
| shared | `components/RecCard.tsx`, `components/IngestForm.tsx`, `components/LoginOverlay.tsx`, `components/SituationPanel.tsx` | Console-token rename (components reused across multiple pages). |
| deps | `package.json`, `package-lock.json` | Added `lucide-react` (icons for sidebar/console chrome). |
| docs | `README.md`, `docs/PRD.md`, `docs/UX_DESIGN.md` | Updated for the operations-console UX direction — PRD gains UI-7…UI-12, README/UX_DESIGN reflect the multi-page console route plan. |
