# UX Design Specification
## Autonomous Multi-Agent AI Platform — Operations Console

**Version:** 1.0
**Date:** 2026-07-24
**Companion to:** PRD.md, TDD.md

---

## 1. Design Principles

1. **Map-first.** Operators scan and act on a map, not reports. Everything else is secondary.
2. **Evidence always visible.** Every recommendation shows its "why" inline — never behind a click (PRD DS-7).
3. **Motion with meaning.** Animation communicates *state change and priority*, never decoration. If it doesn't help someone act faster, it's cut.
4. **Dark-first.** Command centers run 24/7 in low light. Dark theme is the default; light is opt-in.
5. **Calm under load.** A screen with 40 active incidents must still feel scannable, not frantic.

---

## 2. Visual System

### 2.1 Theme — Dark (default) & Light

Design tokens (CSS custom properties). Toggle swaps the `:root` set; everything
else reads from tokens so no component hard-codes a color.

```css
/* ---- Dark (default) ---- */
:root[data-theme="dark"] {
  --bg-base:        #0B0E14;   /* app background */
  --bg-surface:     #141922;   /* panels, cards */
  --bg-surface-2:   #1C2230;   /* raised / hover */
  --border:         #2A3142;
  --text-primary:   #E6EAF2;
  --text-muted:     #8A93A6;
  --accent:         #3B82F6;   /* interactive / focus */

  /* Severity scale — the ONE language, used map + cards + alerts */
  --sev-low:        #22C55E;   /* green  */
  --sev-moderate:   #EAB308;   /* amber  */
  --sev-high:       #F97316;   /* orange */
  --sev-critical:   #EF4444;   /* red    */
  --sev-critical-glow: 0 0 12px rgba(239,68,68,.55);

  --shadow-panel:   0 8px 24px rgba(0,0,0,.45);
  --glass-bg:       rgba(20,25,48,0.85);  /* lite glass: high opacity for readability */
  --glass-blur:     6px;                   /* subtle blur, map stays readable behind */
  --glass-border:   1px solid rgba(42,49,66,0.6);
}

/* ---- Light (opt-in) ---- */
:root[data-theme="light"] {
  --bg-base:        #F5F7FA;
  --bg-surface:     #FFFFFF;
  --bg-surface-2:   #EEF1F6;
  --border:         #D6DCE6;
  --text-primary:   #1A2130;
  --text-muted:     #5A6478;
  --accent:         #2563EB;
  --sev-low:        #16A34A;
  --sev-moderate:   #CA8A04;
  --sev-high:       #EA580C;
  --sev-critical:   #DC2626;
  --sev-critical-glow: 0 0 10px rgba(220,38,38,.45);
  --shadow-panel:   0 6px 18px rgba(20,33,48,.12);
}
```

**Rule:** the severity scale is identical in meaning across dark/light and across
every surface (map heat, alert dot, card border-left). Consistency beats theming.

### 2.2 Typography
- **UI font:** Inter / system-ui. Tabular numerals for counts & timers.
- **Scale:** 12 / 14 / 16 / 20 / 28. Body 14, card titles 16, top-bar counts 20.
- **Never** more than 3 sizes on one panel — reduces scan cost.

### 2.3 Spacing & shape
- 4px base grid (4/8/12/16/24). Cards: 12px radius, 16px padding.
- Panels float over the map with `--glass-bg` + `--glass-blur` backdrop-filter +
  `--shadow-panel`. The **lite glassmorphism** approach:
  - High opacity (0.85) keeps text crisp and readable under pressure
  - Subtle blur (6px) doesn't muddy the map underneath — the blur is visual
    polish, not a functional overlay
  - Strong border defines panel edges clearly
  - Result: modern floating aesthetic without sacrificing clarity (critical for
    disaster response where every second matters)

---

## 3. Information Architecture

The product is an **operations console**, not one overloaded dashboard. `/command`
is the fast overview cockpit; deeper work moves into product-area pages so the
map, alerts, recommendations, resources, medical coordination, routes, and audit
workflows each have enough room.

| Route | Access | Purpose |
|---|---|---|
| `/` | Public | Landing page that explains the platform and routes users to auth. |
| `/login` | Public | Dedicated login page. |
| `/signup` | Public | Request-access / agency signup page. |
| `/forgot-password` | Public | Recovery placeholder UI. |
| `/command` | Authenticated | Operational overview: map preview, critical alerts, AG-8 summary, resource health. |
| `/map` | Authenticated | Full operational map with severity, routes, resources, incidents, and layers. |
| `/alerts` | Operator+ | Alert triage queue and selected-alert detail. |
| `/incidents` | Viewer+ | Active and historical incident list. |
| `/incidents/[id]` | Viewer+ | Single-incident command room. |
| `/recommendations` | Operator+ | Human approval/rejection workspace for agent recommendations. |
| `/resources` | Viewer+ | Hospitals, shelters, teams, ambulances, and capacity status. |
| `/routes` | Viewer+ | Evacuation and response route planning. |
| `/medical` | Operator+ | Hospital capacity, casualty estimates, and ambulance dispatch. |
| `/citizens` | Operator+ | Citizen report verification and trust review. |
| `/agents` | Operator+ | AG-1 through AG-8 activity, latest outputs, and degradation state. |
| `/audit` | Admin / liaison | Decision and recommendation audit trail. |
| `/settings` | Authenticated | Profile, theme, session, and layout preferences. |
| `/citizen` | Public | Citizen-facing assistance, safety guidance, and report intake. |

### 3.1 Public Pages

**Landing page (`/`)**
- Hero: mission-critical tagline, map/radar visual, `Enter Command Center` and
  `Request Access` CTAs.
- Feature bands: multi-agent analysis, real-time map, explainable recommendations,
  human approval gate, auditability.
- How it works: ingest data → normalize events → agent collaboration → human
  approval → live response.
- Trust section: evidence-first outputs, RBAC, audit log, graceful degradation.

**Login (`/login`)**
- Split-screen layout: mission visual on the left, form on the right.
- Fields: username, password, remember-me checkbox, forgot-password link.
- Successful login redirects by role to `/command` first; future role-specific
  defaults can point medical users to `/medical` or field coordinators to `/routes`.

**Signup (`/signup`)**
- Treated as an agency access request, not consumer self-service.
- Fields: full name, email, agency, role request, region/city, password.
- If backend registration is absent, submit state clearly says requests are
  reviewed by administrators.

**Forgot password (`/forgot-password`)**
- Email input and recovery instructions. UI-only until backend support exists.

**Citizen assistance (`/citizen`)**
- Mobile-first page for affected public users.
- Includes language selector, safety guidance, citizen chat, report form, and
  emergency contact information.

### 3.2 Authenticated Console Shell

All authenticated product pages share one shell.

```
┌─────────────────────────────────────────────────────────────┐
│ Top bar: EOC Platform · live feed · incident · search · user │
├──────────────┬──────────────────────────────────────────────┤
│ Sidebar      │ Page content                                 │
│ Command      │                                              │
│ Map          │                                              │
│ Alerts       │                                              │
│ Incidents    │                                              │
│ Recs         │                                              │
│ Resources    │                                              │
│ Routes       │                                              │
│ Medical      │                                              │
│ Citizens     │                                              │
│ Agents       │                                              │
│ Audit        │                                              │
│ Settings     │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

- Desktop: persistent collapsible sidebar, fixed top bar, scrollable page content.
- Mobile/tablet: hamburger drawer, sticky top bar, stacked cards, map panels become
  bottom sheets.
- Top bar owns global liveness: WebSocket state, critical/high counts, clock,
  theme toggle, and current user.
- Sidebar items are filtered by role. Hidden pages must also be route-guarded, not
  just visually hidden.

### 3.3 Authenticated Product Areas

**Command (`/command`)**
- The quick operational overview. It must not become the old congested dashboard.
- Keep: map preview, top 3 critical alerts, AG-8 situation summary, resource health
  mini-cards, layer status, live/reconnecting indicator.
- Move full feeds and detail workflows to their own pages.

```
┌─────────────────────────────────────────────────────────────┐
│ Critical count · high count · live/reconnecting · clock      │
├──────────────┬───────────────────────────────┬──────────────┤
│ Sidebar      │ Map preview                   │ Critical     │
│              │ severity/routes/resources     │ alerts       │
│              │                               │ AG-8 summary │
├──────────────┴───────────────────────────────┴──────────────┤
│ Resource health · citizen report count · latest incident      │
└─────────────────────────────────────────────────────────────┘
```

**Map (`/map`)**
- Full operational map with minimal chrome.
- Left: layer/filter rail. Center: MapLibre canvas. Right/bottom sheet: selected
  incident/resource/route details.
- Map layers: severity heat, resources, routes, incident pins, blocked roads.

**Alerts (`/alerts`)**
- Full triage queue, not a small widget.
- Left: severity/status/agent/time filters and alert list. Right: selected alert
  detail with evidence, rationale, map location, and related recommendation.

**Incidents (`/incidents`)**
- Active and historical incidents list with severity, location, status, age, last
  update, and assigned agencies.
- Clicking an incident opens `/incidents/[id]`.

**Incident command room (`/incidents/[id]`)**
- Incident-scoped workspace.
- Header: disaster type, severity, location, status, last update.
- Main: incident map, AG-8 summary, agent outputs, recommendations, routes,
  resources, citizen reports, and decision timeline.

**Recommendations (`/recommendations`)**
- Human approval gate.
- Tabs: pending, approved, rejected.
- Filters: agent, severity, confidence, incident, agency scope.
- Every card shows action, evidence, rationale, confidence, status, and approve /
  reject controls when allowed.

**Resources (`/resources`)**
- Capacity-first page for hospitals, shelters, teams, ambulances, and supplies.
- Top: summary cards. Middle: category tabs/table. Side: selected resource detail
  and AG-5/AG-4 allocation recommendations.

**Routes (`/routes`)**
- Route-planning page with a large map.
- Shows evacuation paths, blocked roads, vehicle routes, AG-6 rationale, and route
  status (`open`, `blocked`, `degraded`).

**Medical (`/medical`)**
- Medical dispatcher workspace.
- Shows casualty estimates, hospital capacity, ambulance availability, dispatch
  recommendations, and emergency supply gaps.

**Citizens (`/citizens`)**
- Citizen-report review workspace.
- Filters: flagged only, high severity, low trust, recent.
- Each report shows reporter id, message, claimed severity, trust score,
  verification status, and location preview.

**Agents (`/agents`)**
- AI system status page.
- Cards for AG-1 through AG-8: latest output, evidence count, confidence, last run,
  degraded/error state, and blackboard contribution.

**Audit (`/audit`)**
- Admin/liaison page for accountability.
- Table: actor, action, target recommendation/incident, before/after status,
  timestamp, and rationale/evidence reference.

**Settings (`/settings`)**
- Profile, role/agency display, theme, session/logout, layout preferences, and
  notification preferences.

### 3.4 Role-Based Navigation

| Page | Viewer | Operator | Admin |
|---|---:|---:|---:|
| Command | Yes | Yes | Yes |
| Map | Yes | Yes | Yes |
| Alerts | Limited/read | Yes | Yes |
| Incidents | Yes | Yes | Yes |
| Recommendations | Read | Approve/reject | Yes |
| Resources | Yes | Yes | Yes |
| Routes | Yes | Yes | Yes |
| Medical | Read | Yes | Yes |
| Citizens | Read | Yes | Yes |
| Agents | No | Yes | Yes |
| Audit | No | No | Yes |
| Settings | Yes | Yes | Yes |

### 3.5 Drag-and-Drop Customization

`react-grid-layout` is no longer the page architecture. It is limited to optional
overview customization on `/command` only.

- Draggable widgets: critical alerts, AG-8 summary, resource health, recent citizen
  reports, and mini recommendation queue.
- The full feeds and deep workflows live in product-area routes.
- Persistence remains localStorage-first; move to a server-side user layout store
  only when user persistence exists.
- Edit mode remains lock/unlock to prevent accidental drags during active response.

---

## 4. Components & Motion

**Motion engine:** `framer-motion` (React). Global rule: durations 120–260ms,
easing `easeOut` for entrances, `easeInOut` for state changes. Respect
`prefers-reduced-motion` — all of this degrades to instant when the OS asks.

### 4.1 Recommendation card
Evidence inline. Border-left carries severity color.

```
┌─▏🚑 AG-4 Medical · Reroute ambulance #12 ──────────┐
│  → City General  (was: Coastal)                    │
│                                                    │
│  WHY  Coastal at 94% capacity (sensor, 3m ago).    │
│       City General has 12 free beds.               │
│  Confidence ▓▓▓▓▓▓▓▓░░ 0.87                         │
│                                                    │
│  [ ✓ Approve ]   [ ✗ Reject ]   [ Details ⌄ ]      │
└────────────────────────────────────────────────────┘
```

**Animations:**
- **Enter:** slide-up 12px + fade, 200ms `easeOut`. New cards land at top; the
  list below shifts down with a spring (`layout` animation) so nothing "jumps."
- **Approve:** card flashes accent, checkmark draws in (SVG path 180ms), then
  collapses height→0 and fades as it leaves the pending feed. The map pin it
  refers to pulses once in sync — visually links decision → map.
- **Reject:** card desaturates + slides right out, 160ms.
- **New critical:** border-left gets `--sev-critical-glow` and a single
  attention pulse (scale 1→1.02→1, 400ms). One pulse, not a loop — no strobing.

### 4.2 Alerts panel
- **Enter:** stagger-in (each item +40ms delay) so a burst reads as a sequence,
  not a wall.
- **Severity dot:** critical dots have a slow breathing glow (1.8s ease-in-out
  loop, opacity 0.6↔1). This is the *one* looping animation allowed — it's a
  liveness signal that the incident is still active.
- **Dismiss:** swipe-left / fade, 150ms.

### 4.3 Live map (MapLibre)
- **Severity heat overlay:** opacity cross-fades (300ms) when the grid updates —
  no hard repaint flicker.
- **Resource pins (🏥 🚑 🏕️):** drop-in with a small bounce on first appearance.
- **New incident:** an expanding ring (radar ping) plays *once* at its location
  to draw the eye, then settles.
- **Evac routes:** the route line animates its draw (stroke-dashoffset, 500ms)
  from origin → safe zone, so direction of travel is obvious at a glance.
- **Blocked roads:** ✕ marks fade in on the segment; the road segment tints
  `--sev-critical` at low opacity.

### 4.4 Situation bar (AG-8)
- Text updates with a **cross-fade + word-count-aware height ease** so the
  summary refreshing doesn't yank layout. A subtle "updated" shimmer sweeps
  left→right once (400ms) to signal fresh data without a jarring flash.

### 4.5 Theme toggle
- Sun/moon morph (icon path tween, 240ms). Background + surfaces cross-fade
  between token sets over 200ms — no white flash when switching to light.

### 4.6 Global loading / streaming
- WebSocket connected: a 2px top progress bar breathes softly when data streams.
- Disconnected: bar turns `--sev-moderate` and a "reconnecting…" chip slides
  down from the top bar. Operators must *always* know if the feed is live.

---

## 5. Motion Guardrails (so it stays professional, not busy)

| Do | Don't |
|---|---|
| One attention pulse per new critical item | Looping bounce/strobe on anything except the liveness breathing dot |
| Durations 120–260ms | Slow > 400ms transitions that make the UI feel laggy under pressure |
| `layout` springs so lists reflow smoothly | Elements teleporting / jumping when data changes |
| Honor `prefers-reduced-motion` → instant | Forcing animation on users who disabled it |
| Motion that maps to a state change | Decorative motion with no informational meaning |

> `ponytail:` every animation here is tied to a state change or a priority
> signal. If a future addition is "just to look nice," it doesn't ship — motion
> budget is spent on comprehension, not flourish.

---

## 6. Accessibility (non-negotiable)

- Contrast: all text ≥ 4.5:1 on its surface in **both** themes (verify tokens).
  - **Glassmorphism check:** high opacity (`--glass-bg` 0.85) ensures the glass
    effect doesn't reduce text contrast below 4.5:1. Test on live map before
    shipping (red incident markers under glass panels must stay readable).
- Severity is **never** encoded by color alone — always color + icon + label
  (color-blind operators, and it's a life-critical context).
- Full keyboard path: approve/reject reachable without a mouse; visible focus ring (`--accent`).
- `prefers-reduced-motion` disables all non-essential motion (and backdrop-filter blur, which can trigger motion sickness on long shifts).
- Screen-reader live regions announce new critical alerts.

---

## 7. Tech Mapping

| Concern | Choice |
|---|---|
| Framework | Next.js + React + TypeScript (from TDD §2) |
| Styling / tokens | Tailwind CSS + CSS custom properties for theming |
| Glassmorphism | CSS `backdrop-filter: blur(6px)` on panels + high-opacity background (`--glass-bg`) |
| Animation | framer-motion |
| Draggable dashboard | react-grid-layout |
| Map | MapLibre GL (animated layers, `flyTo`, feature-state transitions) |
| Theme persistence | `data-theme` on `<html>` + localStorage → `users.ui_layout` later |

**Glassmorphism implementation note:** `backdrop-filter` is GPU-intensive on older hardware
(pre-2015 machines may stutter). For EOC deployments on legacy workstations, test
on-site; if performance tanks, fall back to solid panels (remove `backdrop-filter`, keep
`--glass-bg` and shadow for the floating effect). The glass-blur blur layer can be
toggled off via a performance mode if needed (deferred, only add if operators complain).

---

## 8. Deliberately deferred (add when operators ask)

- Multiple saved layout *presets* per user (beyond the per-role default).
- Custom per-widget theming.
- 3D terrain / building extrusion on the map.

These add build + maintenance cost without changing decision speed today.
