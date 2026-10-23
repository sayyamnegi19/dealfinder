# Deal Finder UI system

This is the presentation layer for the Deal Finder frontend. It is intentionally
framework-light: Tailwind v4 generates utilities, while the tokens and component
classes live in plain CSS so they are easy to audit and reuse.

## Files

- `src/index.css` — theme tokens, base styles, reduced-motion rules.
- `src/styles/components.css` — reusable component classes.
- `src/App.tsx` — shell, header, footer, skip link.
- `src/pages/SearchPage.tsx` — search form, page grid, search states.
- `src/components/*` — feature components using the primitives below.

## Design principles

1. **Price first.** The result hierarchy is search → best deal → summary → groups.
2. **Evidence over decoration.** Stock, seller, rating, and variant information sit
   next to the offer, not behind a tooltip.
3. **Calm surfaces.** White cards on a neutral canvas, one brand accent, hairline
   borders, and very light shadows.
4. **Native semantics.** Real forms, selects, tables, and dialogs whenever possible.
5. **Readable by default.** No body text below 12px; no low-contrast metadata.
6. **Motion is optional.** Every animation is disabled under
   `prefers-reduced-motion: reduce`.

## Color tokens

Defined in `@theme` in `src/index.css`:

| Token | Value | Use |
| --- | --- | --- |
| `--color-canvas` | `#f8fafc` | Page background |
| `--color-surface` | `#ffffff` | Cards, controls |
| `--color-surface-subtle` | `#f1f5f9` | Nested surfaces, hover |
| `--color-ink-900` | `#0f172a` | Primary text |
| `--color-ink-700` | `#334155` | Body text |
| `--color-ink-600` | `#475569` | Secondary copy |
| `--color-ink-500` | `#64748b` | Metadata (contrast-safe) |
| `--color-line` | `#e2e8f0` | Card and table borders |
| `--color-control` | `#64748b` | Form borders (3:1 UI contrast) |
| `--color-brand-50` | `#ecfdf5` | Best-deal tint |
| `--color-brand-700` | `#047857` | Primary action / links |
| `--color-brand-800` | `#065f46` | Hover / strong brand text |
| `--color-warning` | `#b45309` | Warnings and sample data |
| `--color-danger` | `#be123c` | Errors and destructive actions |
| `--color-info` | `#0369a1` | Informational messages |

Never use `--color-ink-400` for readable text; it is for decorative and disabled
elements only.

## Typography

| Token | Size / line height | Use |
| --- | --- | --- |
| `--text-display` | 32 / 40px | Best-deal price |
| `--text-page-title` | 24 / 32px | Result title |
| `--text-section` | 18 / 26px | Dialog titles, section headings |
| `--text-card-title` | 16 / 24px | Card titles |
| `--text-body-lg` | 16 / 26px | Lead copy |
| `--text-body` | 14 / 22px | Default text |
| `--text-small` | 13 / 20px | Supporting copy |
| `--text-caption` | 12 / 18px | Metadata, helper text |
| `--text-overline` | 12 / 16px | Uppercase labels |

Use `.numeric` on prices, discounts, and table numbers for tabular figures.
Use `.text-meta` for timestamps and secondary metadata.

## Layout tokens

| Token | Default | Desktop |
| --- | --- | --- |
| `--page-gutter` | 16px | 32px |
| `--section-gap` | 24px | 32px |
| `--card-padding` | 16px | 20px |
| `--container` | 1152px | 1152px |
| `--sidebar-width` | — | 304px |

Layout helpers:

- `.container-page` — max width and responsive gutters.
- `.app-shell` — full-height flex column; footer stays at the bottom.
- `.page-grid` — single column, then results + rail at `lg`.
- `.section-stack` — vertical rhythm for cards.
- `.page-rail` — sidebar stack.

## Radii, borders, shadows

- Controls: `--radius-control` (10px).
- Cards: `--radius-card` (16px).
- Dialogs: `--radius-panel` (20px).
- Badges/chips only: pill radius.
- Card border: 1px `--color-line`; control border: 1px `--color-control`.
- Default card shadow: `--shadow-card`; overlay: `--shadow-overlay`.
- No gradients. No hover transforms.

## Components

### Buttons

```tsx
<button className="btn btn-primary">Find best deal</button>
<button className="btn btn-secondary">Retry</button>
<button className="btn btn-ghost btn-icon" aria-label="Close">…</button>
```

Variants: `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-danger`, `btn-link`.
Sizes: `btn-sm`, `btn-lg`, `btn-icon`, `btn-block`.
Use `aria-busy="true"` with a `.spinner` for loading. Do not replace the label with
an icon-only state.

### Fields

```tsx
<div className="field">
  <label className="label" htmlFor="query">Search</label>
  <input id="query" className="input" aria-describedby="query-help" />
  <p id="query-help" className="field-help">Include the model number.</p>
</div>
```

Use `.select` for native selects (it includes a consistent chevron) and
`.textarea` for multi-line input. Set `aria-invalid="true"` and pair it with
`.field-error` when validation fails.

### Cards

```tsx
<section className="card">
  <div className="card-header">
    <h2 className="card-title">Title</h2>
    <span className="badge badge-neutral">2 offers</span>
  </div>
  <p className="card-description">Supporting text</p>
</section>
```

Use `card-brand` for the best-deal surface. Use `card-interactive` only when the
whole card is clickable.

### Navigation and shell

`.site-header`, `.brand`, `.brand-mark`, `.nav-link`, `.site-footer`.
The current app has no secondary navigation; `.nav-link` is ready for a future
nav without adding a new route now.

### Badges

`badge` plus one of `badge-neutral`, `badge-brand`, `badge-success`,
`badge-warning`, `badge-danger`, `badge-info`, `badge-site-amazon`,
`badge-site-flipkart`.

Badges always contain text. Color is never the only signal.

### Alerts

`alert` plus `alert-info`, `alert-success`, `alert-warning`, or `alert-danger`.
Use `.alert-title`, `.alert-body`, and optional `.alert-action`.

### Tables

`.table-wrap` → `.table`; add `.table-num` to numeric cells. Tables have a
minimum width and scroll horizontally on small screens. Use `.table-empty` for
an empty state. No table exists in the current UI; the styles are ready for a
comparison or admin view.

### Dialogs

Use a native `<dialog>`:

```tsx
<dialog className="dialog" aria-labelledby="dialog-title">
  <div className="dialog-header">
    <h2 id="dialog-title" className="dialog-title">Title</h2>
    <button className="dialog-close" aria-label="Close">×</button>
  </div>
  <div className="dialog-body">…</div>
  <div className="dialog-footer">…</div>
</dialog>
```

Native `<dialog>` handles Escape and focus trapping. Open it with
`dialog.showModal()` so it enters the top layer and displays the backdrop; the
system styles the backdrop, responsive width, header, body, footer, and close
button.

### Status and feedback

- `.status-panel` — agent progress container.
- `.status-dot`, `.status-dot--brand`, `.status-dot--muted`, `.is-running`.
- `.spinner` — loading indicator.
- `.skeleton` — opacity pulse, no gradient shimmer.
- `.empty-state` — dashed empty container; use `.empty-state--compact` inside a
  card.
- `.log`, `.log-line`, `.log-line--ok`, `.log-line--fail`, `.log-line--muted` —
  technical trace, hidden behind `Search details` after completion.
- `.details` — native disclosure for secondary technical information.

## State rules

| Component | Hover | Focus | Active | Disabled | Loading | Error |
| --- | --- | --- | --- | --- | --- | --- |
| Buttons | darken surface | 2px brand outline | darker surface | opacity + not-allowed | spinner + `aria-busy` | danger variant |
| Inputs/selects | darker border | brand outline + soft ring | — | muted surface | — | danger border + text |
| Cards | border/shadow only when interactive | — | — | — | skeleton | alert inside |
| Badges | — | — | — | — | — | semantic variant |
| Tables | row tint | native | — | — | skeleton | empty row |

Use `:focus-visible`, not `:focus`, for keyboard focus. Never remove outlines
without a visible replacement.

## Responsive rules

- **320–639px:** single column, 16px page gutter, full-width primary controls,
  offer rows stack, brand tagline hidden below 380px.
- **640–1023px:** 24px gutter, search controls can share a row, cards use 20px
  padding.
- **1024px+:** 32px gutter, results plus 304px history rail.
- Tables scroll horizontally; dialogs stay within 16px side margins.
- Primary controls are 40px high and chips are 36px; keep critical touch
  targets at least that large and use 44px where the layout allows.

## Accessibility checklist

- Text contrast ≥ 4.5:1; UI boundaries and focus rings ≥ 3:1.
- No text below 12px.
- Every control has a visible label, not only a `title`.
- Streaming updates use a polite live region for milestones, not every event.
- `prefers-reduced-motion` disables smooth scrolling and looping animations.
- Alerts use appropriate roles where the content is urgent.
- External links announce that they open in a new tab.
- Tables use `<caption>`, `<thead>`, and `<th scope="col">` when built.
- Dialogs use native `<dialog>` and `aria-labelledby`.
