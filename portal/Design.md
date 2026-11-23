# Frontend Design System

## Purpose

This document is the implementation contract for building a modern, polished frontend. It is
portable: an agent should be able to apply it to another React, Next.js, or Vite project without
copying this application's business logic.

Use this design system for:

- authenticated dashboards and operational tools;
- data-heavy analytics interfaces;
- forms with meaningful, user-editable values;
- reports, charts, tables, and result screens;
- marketing-adjacent product pages that need a restrained editorial feel.

Do not use this system as a generic "template." Preserve information hierarchy, accessibility,
and the existing component architecture. When a new pattern is needed, extend these tokens and
primitives instead of introducing disconnected colors or one-off styles.

---

## 1. Design Direction

Build a quiet, precise, analytical interface inspired by modern developer tools and premium
Supabase-style product surfaces.

The visual personality is:

- neutral and crisp;
- high-density where data demands it;
- calm rather than decorative;
- confident through typography and spacing;
- green as a positive/action color;
- crimson for danger or destructive states;
- dark for depth and navigation, not for every surface;
- technically polished, never playful or glossy.

### Visual Principles

1. **Clarity before decoration**  
   Every visual decision should improve hierarchy, comprehension, or task completion.

2. **Light surfaces, strong ink**  
   Use white or near-white canvases in light mode. Use almost-black surfaces in dark mode.
   Avoid flat gray dashboards with no hierarchy.

3. **One accent, used deliberately**  
   Emerald green is reserved for positive, primary, and active experiences. Do not make every
   component green.

4. **Borders are structural**  
   Prefer thin borders and subtle shadows over large cards or excessive rounded containers.

5. **Data is a first-class citizen**  
   Charts and metrics should be readable at a glance. Axis lines, labels, legends, and tooltips
   must share the same semantic color system.

6. **Dense but breathable**  
   Compact controls and tight table rows are appropriate. Surround the interface with consistent
   section spacing so the density does not feel crowded.

---

## 2. Stack and Styling Contract

The preferred implementation stack is:

- React with TypeScript;
- Vite or Next.js;
- Tailwind CSS for layout and utilities;
- shadcn/ui or Radix primitives for accessible behavior;
- Lucide-style icon components;
- Recharts or another typed chart library;
- CSS variables for theme and semantic color tokens.

Use semantic Tailwind tokens such as `bg-background`, `text-foreground`, `border-border`,
`bg-card`, `text-muted-foreground`, and `bg-primary`. Do not hardcode page colors when a semantic
token exists.

CSS variables should be HSL triplets in light and dark themes. This supports Tailwind opacity
modifiers and keeps theme switching consistent:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 0 0% 9%;
  --card: 0 0% 100%;
  --card-foreground: 0 0% 9%;
  --primary: 152 60% 53%;
  --primary-foreground: 0 0% 9%;
  --secondary: 0 0% 96%;
  --secondary-foreground: 0 0% 9%;
  --muted: 0 0% 98%;
  --muted-foreground: 0 0% 44%;
  --accent: 0 0% 96%;
  --accent-foreground: 0 0% 9%;
  --destructive: 343 100% 44%;
  --destructive-foreground: 0 0% 100%;
  --success: 152 60% 53%;
  --success-foreground: 0 0% 9%;
  --warning: 45 93% 47%;
  --warning-foreground: 0 0% 9%;
  --border: 0 0% 87%;
  --input: 0 0% 87%;
  --ring: 152 60% 53%;
  --radius: 0.75rem;
}

.dark {
  --background: 0 0% 7%;
  --foreground: 0 0% 98%;
  --card: 0 0% 11%;
  --card-foreground: 0 0% 98%;
  --primary: 152 60% 53%;
  --primary-foreground: 0 0% 9%;
  --secondary: 0 0% 15%;
  --secondary-foreground: 0 0% 98%;
  --muted: 0 0% 15%;
  --muted-foreground: 0 0% 65%;
  --accent: 0 0% 15%;
  --accent-foreground: 0 0% 98%;
  --destructive: 343 100% 50%;
  --destructive-foreground: 0 0% 100%;
  --success: 152 60% 53%;
  --success-foreground: 0 0% 9%;
  --warning: 45 93% 58%;
  --warning-foreground: 0 0% 9%;
  --border: 0 0% 20%;
  --input: 0 0% 20%;
  --ring: 152 60% 53%;
}
```

Configure Tailwind to consume these variables rather than duplicating raw hex values throughout
the JSX.

---

## 3. Color System

### Brand and Semantic Palette

| Role | Light | Dark / usage |
| --- | --- | --- |
| Green primary | `#3ecf8e` | Primary actions and success |
| Green deep | `#24b47e` | Hover and emphasized success |
| Crimson danger | `#e2005a` | Errors, churn, destructive actions |
| Ink | `#171717` | Headlines and dark surfaces |
| Ink secondary | `#212121` | Elevated dark surface |
| Medium gray | `#707070` | Secondary text |
| Hairline | `#dfdfdf` | Borders and separators |
| Canvas | `#ffffff` | Primary light surface |
| Canvas muted | `#fafafa` | Subtle backgrounds |

Additional neutral grays should stay within a consistent monochrome ramp. Avoid introducing
blue-tinted grays unless they serve a product-specific domain.

### Semantic Usage

- **Success / Low risk:** green
- **Warning / Medium risk:** amber or violet, but never red
- **Danger / High risk:** crimson
- **Neutral / Default:** monochrome
- **Informational:** muted foreground and hairline borders

Crimson is not a general accent. Use it only for actual negative or destructive meaning.

Charts may use a stable palette independent of UI semantics:

- stayed / positive: green
- churned / negative: crimson
- medium risk: violet or amber
- neutral series: near-black or warm gray
- remaining series: light gray

Never encode meaning by color alone. Pair color with labels, icons, patterns, or text.

---

## 4. Typography

Use a high-quality neutral sans-serif. The implementation may use Inter or a system sans-serif
stack. Do not load multiple display fonts.

```css
body {
  font-family: Inter, "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
```

### Type Scale

| Use | Size | Weight | Tracking |
| --- | ---: | ---: | --- |
| Page title | 32–36 px | 500–600 | `-0.02em` |
| Section title | 18–20 px | 500–600 | `-0.01em` |
| Card title | 16–18 px | 500 | normal |
| KPI value | 28–32 px | 500 | `-0.02em` |
| Body | 14–16 px | 400 | normal |
| Metadata / label | 12–13 px | 500 | normal |
| Tiny status text | 11 px | 600 | `0.01em` |

Avoid long headings that occupy the full viewport. Page titles should remain within approximately
760 px for comfortable reading.

Page titles use:

```css
.page-title {
  max-width: 48rem;
  font-size: clamp(2rem, 4vw, 2.25rem);
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.02em;
}
```

Numbers and data labels should be tabular when available:

```css
.numeric {
  font-variant-numeric: tabular-nums;
}
```

---

## 5. Spacing, Radius, and Density

Use an 4 px base spacing scale:

```text
4, 8, 12, 16, 20, 24, 32, 40, 48, 64
```

Default page padding is:

- 24 px on mobile;
- 32 px on desktop;
- 40 px for very large, sparse workspaces.

Default cards use 24 px padding. Dense cards or chart panels may use 16–24 px.

### Radius

| Element | Radius |
| --- | --- |
| Buttons and inputs | 8 px |
| Cards and panels | 12 px |
| Pills and badges | 999 px or 6 px for status labels |
| Icons in containers | 8 px |
| Tooltips and menus | 8–12 px |

Do not use 16–24 px radius on every primitive. Use rounded corners to establish hierarchy, not as
a trend.

### Elevation

Use low elevation for resting cards and stronger elevation only on overlays or hover.

```css
.card-shadow {
  box-shadow: 0 1px 3px rgb(0 0 0 / 6%);
}

.card-shadow-hover {
  box-shadow: 0 8px 24px rgb(0 0 0 / 8%);
}

.dark .card-shadow {
  box-shadow: 0 1px 3px rgb(0 0 0 / 35%);
}
```

---

## 6. Layout

Use a sidebar-based application shell for dashboard products.

### Application Shell

- fixed or sticky top bar;
- collapsible icon sidebar on desktop;
- off-canvas or overlay navigation on mobile;
- viewport-height content area;
- one continuous main content column;
- sidebar and header borders instead of heavy shadows.

Header height: 64 px.

Page content should be max-width constrained:

```html
<main class="mx-auto max-w-[1280px] px-4 py-6 sm:px-6 lg:px-8">
  <!-- content -->
</main>
```

### Page Structure

Every primary page should have:

1. optional status pill or breadcrumb;
2. page title;
3. short supporting lead;
4. primary and secondary actions;
5. KPI or summary row;
6. analysis, charts, tables, or form sections;
7. optional footer action area.

Use a border-bottom on the hero only when it provides a clear section break. Do not use a hero
banner for simple operational pages.

### Dashboard Grid

Use responsive grids:

```html
<section class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
  <!-- KPI cards -->
</section>

<section class="grid grid-cols-1 gap-5 lg:grid-cols-5">
  <div class="lg:col-span-3"><!-- wide chart --></div>
  <div class="lg:col-span-2"><!-- side chart --></div>
</section>
```

Do not make every chart the same height. The layout should reflect analytical importance while
keeping each panel visually stable.

---

## 7. Components

### Page Hero

A page hero is a title block, not a decorative banner.

Required properties:

- `title`;
- optional `lead`;
- optional `badge`;
- optional actions.

Implementation:

```tsx
<header className="border-b border-border pb-8">
  <span className="mb-4 inline-flex rounded-full bg-success/10 px-2.5 py-1 text-xs font-medium text-success">
    Live dashboard
  </span>
  <h1 className="max-w-3xl text-[32px] font-medium leading-[1.15] tracking-[-0.02em] sm:text-[36px]">
    Churn intelligence at a glance
  </h1>
  <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
    Business health snapshot for today.
  </p>
</header>
```

### Surface Card

Use card surfaces for self-contained information groups. Cards should contain exactly one
primary concept.

```tsx
<section className="rounded-xl border border-border bg-card p-6 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
  <div className="mb-5 flex items-start justify-between gap-4">
    <div>
      <h2 className="text-lg font-medium">Card title</h2>
      <p className="mt-1 text-[13px] text-muted-foreground">Supporting context</p>
    </div>
  </div>
  {/* Content */}
</section>
```

Do not nest multiple large cards inside a card.

### KPI Card

Each KPI card should include:

- icon or data category marker;
- title;
- prominent value;
- optional delta;
- optional semantic accent;
- no more than one supporting label.

```tsx
<article className="rounded-xl border border-border bg-card p-6 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
  <div className="mb-4 flex items-start justify-between">
    <div className="flex h-10 w-10 items-center justify-center rounded-md border bg-success/10 text-success">
      <Users className="h-5 w-5" />
    </div>
  </div>
  <p className="text-[13px] text-muted-foreground">Total customers</p>
  <p className="mt-1 text-[28px] font-medium leading-tight tracking-[-0.02em]">12,480</p>
</article>
```

Use a 4 px semantic left accent only when it improves scanning. Do not combine the left accent
with a large background fill.

### Buttons

Primary button:

```tsx
<button className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-[#24b47e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
  Continue
</button>
```

Secondary button:

```tsx
<button className="inline-flex h-10 items-center justify-center rounded-md border border-border bg-card px-4 text-sm font-medium transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
  Cancel
</button>
```

Rules:

- one primary action per screen region;
- secondary actions use outline or ghost styling;
- destructive actions use crimson only at the moment of final confirmation;
- disabled controls use opacity and `not-allowed`;
- icon-only actions require an accessible label or tooltip.

### Inputs and Forms

Use consistent 40 px control height.

```tsx
<div className="space-y-2">
  <label htmlFor="company" className="text-sm font-medium">Company</label>
  <input
    id="company"
    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none transition-shadow placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
  />
  <p className="text-xs text-muted-foreground">Used to personalize recommendations.</p>
</div>
```

Forms should be:

- labeled explicitly;
- keyboard navigable;
- visually grouped into logical sections;
- validated inline;
- safe from layout jumps by reserving error/help space where practical.

Use fieldsets for related option groups.

### Status and Badges

Status components should remain small and semantically strong:

```tsx
<span className="inline-flex items-center gap-1.5 rounded-md border border-destructive/20 bg-destructive/10 px-2 py-0.5 text-[11px] font-semibold text-destructive">
  <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
  High risk
</span>
```

Do not write status-only text in all-caps unless it is a short conventional label.

### Tables

Tables should favor:

- sticky header when appropriate;
- 48 px or denser 40 px row height;
- 12–14 px text;
- right-aligned numeric columns;
- status at the beginning or end, never buried;
- one clear row hover state;
- horizontal scrolling for mobile instead of compressed columns.

Use real table markup for tabular data. Do not use CSS grid for a table unless it is not
semantically tabular.

### Charts

Chart panels should use the same `SurfaceCard` primitive as other content cards.

Rules:

- remove vertical grid lines for area charts unless readability requires them;
- use horizontal dashed grid lines sparingly;
- omit unhelpful axis borders;
- use 2–3 px line strokes;
- make active dots visible but restrained;
- use custom tooltips with semantic text color;
- show legends for multi-series charts;
- avoid pie charts for precise comparisons;
- provide a textual summary or table fallback for key results.

For chart tooltips:

```tsx
<div className="rounded-md border border-border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
  <p className="font-medium">January</p>
  <p className="mt-0.5 font-medium text-primary">42%</p>
</div>
```

---

## 8. Navigation

### Sidebar

- 64 px header;
- 16 px horizontal item padding;
- 40 px navigation item height;
- 8 px item radius;
- icon-first;
- active item uses a subtle tint plus a strong icon or indicator;
- inactive items use muted foreground.

The sidebar should be almost black in both themes. In light mode, the white content canvas and
dark sidebar create enough contrast without additional shadows.

### Header

- 64 px sticky top bar;
- bottom hairline;
- blurred translucent background for polished scrolling;
- title on desktop;
- sidebar trigger on the left;
- utility actions on the right.

```tsx
<header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 sm:px-6">
  {/* Navigation and utilities */}
</header>
```

---

## 9. Responsive Behavior

Use a mobile-first approach.

Recommended breakpoints:

- `sm`: 640 px
- `md`: 768 px
- `lg`: 1024 px
- `xl`: 1280 px
- `2xl`: 1536 px

Responsive rules:

- sidebar collapses or becomes a sheet below desktop;
- header title may be hidden on mobile;
- KPI cards become 2 columns at small widths and 4 columns at large widths;
- wide chart spans are responsive and stacked;
- content uses horizontal containment rather than shrinking charts beyond legibility;
- tables scroll horizontally;
- hero actions wrap;
- form columns collapse into one column;
- sticky actions should remain reachable without covering content.

Never hide essential data solely to fit mobile. Replace the layout rather than the meaning.

---

## 10. Dark Mode

Dark mode is a real theme, not an inverted filter.

Rules:

- canvas: `hsl(0 0% 7%)`;
- cards: `hsl(0 0% 11%)`;
- elevated surfaces: `hsl(0 0% 15%)`;
- borders: `hsl(0 0% 20%)`;
- body text: `hsl(0 0% 98%)`;
- muted text: `hsl(0 0% 65%)`;
- preserve green and crimson contrast;
- slightly reduce chart grid intensity;
- increase card shadows to maintain depth.

Respect system preference on first load, persist an explicit user choice, and apply the class
before React rendering to avoid a flash.

Theme storage should be namespaced to the product.

```ts
const storedTheme = localStorage.getItem("app-theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
const resolved = storedTheme === "dark" || (!storedTheme && prefersDark)
  ? "dark"
  : "light";

document.documentElement.classList.add(resolved);
```

---

## 11. Motion

Motion should communicate state, not entertain.

Use:

- 150–200 ms for color and opacity transitions;
- 200–300 ms for panels and drawers;
- ease-out for entrances;
- ease-in-out for reversible transitions;
- no bouncing or overshoot;
- subtle skeleton shimmer or opacity pulse for loading.

Cards may elevate on hover:

```css
.interactive-card {
  transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

.interactive-card:hover {
  border-color: hsl(var(--border));
  box-shadow: 0 8px 24px rgb(0 0 0 / 8%);
  transform: translateY(-1px);
}
```

Do not animate layout continuously. In data visualizations, animate between meaningful states
only, and provide reduced-motion behavior.

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 12. Loading, Empty, and Error States

Every asynchronous surface needs an explicit state.

### Loading

- use compact skeletons for cards and charts;
- keep the layout dimensions stable;
- do not replace a complete screen with a full-page spinner;
- label background work only when the wait is long.

### Empty

Include:

- a simple icon or visual marker;
- a concise explanation;
- the reason no data exists;
- one relevant action.

Example:

```tsx
<div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed border-border px-6 text-center">
  <SearchX className="mb-3 h-8 w-8 text-muted-foreground" />
  <h3 className="font-medium">No results found</h3>
  <p className="mt-1 max-w-sm text-sm text-muted-foreground">
    Try changing the filters or uploading a new dataset.
  </p>
  <button className="mt-4 rounded-md border border-border px-4 py-2 text-sm">
    Reset filters
  </button>
</div>
```

### Error

- explain what failed;
- retain usable context;
- provide retry or correction;
- never silently fall back to fake success data;
- use destructive styling only for the state itself.

---

## 13. Accessibility

Accessibility is required, not a final polish pass.

- use semantic HTML;
- preserve a logical heading order;
- provide visible keyboard focus;
- maintain at least 4.5:1 contrast for normal text;
- maintain at least 3:1 contrast for meaningful UI borders and icons;
- do not rely on hover for essential information;
- pair icon-only controls with labels;
- use `aria-live` only for meaningful status updates;
- keep dialogs and menus Radix-accessible or equivalent;
- return focus after closing dialogs;
- support Escape for overlays;
- provide labels and descriptions for form controls;
- ensure charts have accessible summaries or equivalent data tables.

Focus ring pattern:

```css
:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}
```

Avoid removing outlines without replacing them with an equally visible ring.

---

## 14. Component Architecture

Separate the UI into:

- `components/ui/` — low-level shadcn/Radix primitives;
- `components/` — reusable application components;
- `pages/` or `app/` — routed compositions;
- `lib/` — API types, chart themes, helpers, and design constants;
- `hooks/` — reusable state and browser behavior;
- `test/` — component and integration tests.

Reuse primitives before creating variants.

Good candidates for reusable components:

- `AppShell`;
- `PageHero`;
- `SurfaceCard`;
- `ChartPanel`;
- `KpiCard`;
- `StatusBadge`;
- `FilterBar`;
- `DataTable`;
- `EmptyState`;
- `ErrorState`;
- `ThemeToggle`.

Component APIs should be typed and small:

```tsx
interface ChartPanelProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  padding?: "sm" | "md" | "lg";
}
```

Avoid passing arbitrary string design variants like `"prettyCard"` or `"darkGreenPanel"`.
Express them with semantic props or composition.

---

## 15. Data Visualization Tokens

Keep chart colors in a dedicated module.

```ts
export const CHART = {
  stayed: "#3ecf8e",
  stayedDeep: "#24b47e",
  churned: "#e2005a",
  rollingLine: "#24b47e",
} as const;

export const RISK = {
  low: "#3ecf8e",
  medium: "#644fc1",
  high: "#e2005a",
} as const;
```

Theme chart surfaces:

```ts
export const chartTheme = {
  grid: "var(--sb-grid)",
  tick: {
    fill: "var(--sb-tick)",
    fontSize: 12,
  },
  tooltip: {
    backgroundColor: "var(--sb-tooltip-bg)",
    border: "1px solid var(--sb-tooltip-border)",
    borderRadius: "8px",
    color: "var(--sb-tooltip-text)",
  },
};
```

Use CSS variable-backed chart theme values so charts also change with the product theme.

---

## 16. Modern CSS Utilities

Add small reusable utility classes for repeated layout patterns:

```css
@layer utilities {
  .card-shadow {
    box-shadow: 0 1px 3px rgb(0 0 0 / 6%);
  }

  .dark .card-shadow {
    box-shadow: 0 1px 3px rgb(0 0 0 / 35%);
  }

  .card-shadow-hover {
    box-shadow: 0 8px 24px rgb(0 0 0 / 8%);
  }

  .dark .card-shadow-hover {
    box-shadow: 0 8px 24px rgb(0 0 0 / 40%);
  }

  .display-tight {
    letter-spacing: -0.02em;
  }

  .numeric {
    font-variant-numeric: tabular-nums;
  }

  .scrollbar-subtle {
    scrollbar-width: thin;
  }

  .scrollbar-subtle::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  .scrollbar-subtle::-webkit-scrollbar-thumb {
    border: 2px solid transparent;
    border-radius: 999px;
    background: hsl(var(--muted-foreground) / 35%);
    background-clip: padding-box;
  }
}
```

Use `:where()` for low-specificity component resets only when needed.

```css
:where(button, input, textarea, select) {
  font: inherit;
}
```

Avoid excessive custom CSS. Tailwind utilities should handle composition while CSS variables
and small reusable classes handle theme-level consistency.

---

## 17. Implementation Checklist

Before completing a frontend implementation, verify:

- [ ] semantic theme tokens are defined in light and dark modes;
- [ ] no raw one-off page backgrounds replace `background` or `card`;
- [ ] the shell has a consistent header and sidebar;
- [ ] primary pages have clear hierarchy;
- [ ] each card contains one coherent concept;
- [ ] KPI values are easy to scan;
- [ ] charts have labels, tooltips, and stable theme colors;
- [ ] form controls have labels and visible focus;
- [ ] loading, empty, and error states exist;
- [ ] all actions work on keyboard;
- [ ] icon-only controls have accessible names;
- [ ] responsive layouts have been checked at 375, 768, 1024, and 1440 px;
- [ ] reduced motion is supported;
- [ ] no horizontal overflow appears unexpectedly;
- [ ] dark mode preserves contrast and borders;
- [ ] API failures do not show success-shaped fallbacks.

---

## 18. Prompt for Agents

Use this instruction with implementation agents:

> Implement the requested interface using the design system in `Design.md`. Preserve the
> neutral, analytical visual language; use semantic CSS variables and Tailwind tokens; keep
> cards compact and structurally bordered; use emerald green for primary and positive states
> and crimson for danger; provide polished light and dark themes; use accessible shadcn/Radix
> primitives; build responsive layouts for mobile and desktop; include loading, empty, and
> error states; do not introduce gradients, oversized radii, decorative illustrations, or
> unrelated visual styles. Verify keyboard navigation, focus states, chart labels, and layout
> at 375 px, 768 px, 1024 px, and 1440 px.
