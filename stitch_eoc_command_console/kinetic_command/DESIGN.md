---
name: Kinetic Command
colors:
  surface: '#10131a'
  surface-dim: '#10131a'
  surface-bright: '#363941'
  surface-container-lowest: '#0b0e15'
  surface-container-low: '#191b23'
  surface-container: '#1d2027'
  surface-container-high: '#272a31'
  surface-container-highest: '#32353c'
  on-surface: '#e1e2ec'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e1e2ec'
  inverse-on-surface: '#2e3038'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#c2c6d3'
  on-secondary: '#2c313a'
  secondary-container: '#474b56'
  on-secondary-container: '#b7bcc8'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#dee2ef'
  secondary-fixed-dim: '#c2c6d3'
  on-secondary-fixed: '#171c25'
  on-secondary-fixed-variant: '#424751'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#10131a'
  on-background: '#e1e2ec'
  surface-variant: '#32353c'
typography:
  display-header:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '700'
    lineHeight: 20px
    letterSpacing: 0.05em
  body-compact:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  data-tabular:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  data-metric-lg:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 24px
  label-caps:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.08em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  container-margin: 16px
  gutter: 8px
---

## Brand & Style

The design system is engineered for high-stakes, high-density environments where cognitive load management is paramount. It prioritizes rapid information ingestion and visual hierarchy through a refined **Glassmorphic** aesthetic. 

The personality is professional, calm, and technical. By utilizing translucent layers and backdrop blurs, the UI maintains spatial context—allowing operators to see underlying map data or secondary streams while interacting with foreground controls. The visual language balances "heavy" data with "light" aesthetics, ensuring that even the most information-dense screens feel organized and breathable.

**Key Principles:**
- **Visual Precision:** Every pixel serves a purpose. Borders are thin, and margins are tight but consistent.
- **Atmospheric Depth:** Depth is communicated via varying levels of translucency and blur, rather than traditional drop shadows.
- **Functional Density:** Optimized for 4K command displays and multi-monitor setups where maximizing data real estate is critical.

## Colors

The palette is anchored in deep charcoals and navy-tints for the dark mode to reduce eye strain during long shifts. The light mode variant maintains professional integrity through high-contrast grays and crisp whites.

### Semantic Signaling
Color is never used as the sole indicator of status. Every severity level (Low to Critical) must be accompanied by an icon and specific text labels. 
- **Critical Status:** Includes a subtle "breathing" glow (2px spread, 10% opacity) in the accent color to draw peripheral attention without causing distraction.
- **Glass Surfaces:** Dark mode uses `rgba(20, 25, 48, 0.85)` with a `12px` backdrop blur. Light mode uses `rgba(255, 255, 255, 0.8)` with the same blur intensity.

## Typography

Typography is highly specialized for technical utility.
- **Geist Sans:** Used for all UI chrome, navigation, and descriptive text. It provides high legibility at the small scales required for density.
- **JetBrains Mono:** Reserved for all dynamic data, coordinates, timestamps, and IDs. The monospaced nature ensures that metrics do not "jump" or shift horizontally when values update in real-time.
- **Headers:** All section headers should use `label-caps` or `display-header` styles to create clear visual separation between data modules.

## Layout & Spacing

This design system utilizes a **Fixed Grid** system optimized for dashboard tiling. 
- **The 4px Rule:** All spacing increments must be multiples of 4px.
- **Density:** Components use `sm` (8px) for internal padding and `md` (12px) for external gaps.
- **Layout Model:** A 12-column grid is used for the main dashboard. Sidebars are fixed at 280px (collapsed to 64px). 
- **Z-Index Strategy:** Map layers sit at the base (z-0). Glass panels and data widgets sit at (z-10). Overlays, alerts, and modals sit at (z-100).

## Elevation & Depth

Depth is achieved through layering and edge treatment rather than shadows. 
- **Surface Level 0:** The base background (Base Background color).
- **Surface Level 1:** Translucent glass panels. These feature a 1px inner border (`#2a3142` in dark) to define the edge against the background.
- **Surface Level 2:** Hover states or active selections. These use the "Elevated Surface" color with a slightly higher opacity (0.95).
- **Glass Effects:** Every panel must utilize `backdrop-filter: blur(12px)` to ensure text remains readable over complex map textures or video streams.

## Shapes

The design system uses a consistent **12px (rounded-lg)** corner radius for all primary panels and cards. 
- **Sub-components:** Internal elements like input fields or buttons use a **6px** radius to maintain a nested aesthetic.
- **Interactive Elements:** Checkboxes and radio buttons use a **2px** radius for a sharper, more technical feel.

## Components

### Recommendation Cards
- **Structure:** 12px rounded glass panel. 
- **Indicators:** A 4px solid vertical border on the left side, color-coded by severity.
- **Critical Alert:** For critical items, apply a CSS animation `pulse-glow` using the Critical Error color at 10% opacity.

### Navigation Sidebar
- **Visuals:** Slim profile (64px or 280px). 
- **Interactive:** Active states use a subtle primary-color tint (10% opacity) and a 2px vertical accent line on the left.

### Input Fields
- **Style:** Ghost-style inputs with a 1px border.
- **Focus State:** Border changes to Primary Color with a subtle outer glow.
- **Typography:** Uses `body-compact` for input text and `label-caps` for field labels.

### Data Tables
- **Styling:** No vertical borders. Subtle horizontal dividers (1px).
- **Metrics:** All numerical data must use `data-tabular` (JetBrains Mono) to ensure alignment across rows.
- **Header:** Sticky headers with a background blur to maintain context during scrolling.

### Map Overlays
- **Visuals:** Floating glass containers with `sm` (8px) padding. 
- **Placement:** Anchored to corners with 16px margins from the screen edge.