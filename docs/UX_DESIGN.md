# UX Design Specification
## Autonomous Multi-Agent AI Platform — EOC Dashboard

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

## 3. Layout (with resizable / draggable regions)

```
┌─────────────────────────────────────────────────────────────────┐
│ TOP BAR  region · 🔴3 crit 🟠5 high · clock · theme⏾ · agency 👤 │
├──────────┬──────────────────────────────────────────┬───────────┤
│ LEFT     │                                          │ RIGHT     │
│ (dock)   │              LIVE MAP                     │ (dock)    │
│ Filters  │        MapLibre · layered · animated      │ Alerts ▲  │
│ Layers   │                                          │ Recs   ▲  │
│ Legend   │                                          │           │
├──────────┴──────────────────────────────────────────┴───────────┤
│ SITUATION BAR — AG-8 rolling summary (auto-refresh, plain lang)   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 Drag-and-drop customization
- **Library:** `react-grid-layout` (widget grid) — panels are draggable +
  resizable tiles the operator can rearrange.
- **Draggable widgets:** Alerts, Recommendations, Filters/Layers, Situation
  summary, Resource status, Citizen-report inbox.
- **The map is the pinned canvas** — it fills remaining space and is *not* a
  draggable tile (it's the ground the widgets float over).
- **Persistence:** layout saved per user (localStorage first; `users.ui_layout`
  JSON column when RBAC lands). Each role ships a sensible default layout
  (Medical Dispatcher, Rescue Coordinator, etc. — PRD UI-5).
- **Edit mode:** a lock/unlock toggle. Locked = no accidental drags mid-incident
  (critical — you don't want to move a panel while approving a rescue).

```
┌ Edit Layout ⇆ ┐   drag handles appear, tiles get a dashed outline,
└───────────────┘   grid snap guides fade in. Toggle off → guides fade out.
```

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
