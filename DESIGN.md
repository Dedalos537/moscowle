# EdySync Design System

## Brand

| Token | Value |
|---|---|
| Name | Centro de Terapias Juan Pablo II |
| Tagline | "Tu centro de terapias de confianza" |
| Personality | Professional, warm, trustworthy |

## Color Palette

### Light (default `@theme`)

| Token | Value | Usage |
|---|---|---|
| `--color-primary` | `#75a83a` | Buttons, active states, links |
| `--color-background` | `#f8fbed` | Page background |
| `--color-surface` | `#f8fbed` | Cards, modals, dropdowns |
| `--color-surface-container-lowest` | `#ffffff` | Elevated surfaces |
| `--color-surface-container-low` | `#f3f5e7` | Subtle hover |
| `--color-surface-container` | `#edefe2` | Default surface |
| `--color-surface-container-high` | `#e7e9dc` | Header, sidebar |
| `--color-surface-container-highest` | `#e1e4d7` | Active hover |
| `--color-on-surface` | `#191d15` | Primary text |
| `--color-on-surface-variant` | `#43493a` | Secondary text |
| `--color-outline-variant` | `#c3c9b5` | Borders, dividers |
| `--color-outline` | `#737968` | Strong borders |
| `--color-border` | `#e1e4d7` | Card borders |

### Semantic

| Token | Value | Usage |
|---|---|---|
| `--color-success` | `#2e7d32` | Completed, present |
| `--color-warning` | `#d97706` | In progress, pending |
| `--color-error` | `#ba1a1a` | Cancelled, absent, errors |
| `--color-info` | `#2563eb` | Scheduled, info |

### Dark Mode

Defined in `.dark` block. All light tokens have dark equivalents via `var()`.

## Typography

| Style | Size | Weight | Line Height | Letter Spacing |
|---|---|---|---|---|
| `text-h1` | 48px | 800 | 1.2 | -0.02em |
| `text-h2` | 32px | 700 | 1.3 | -0.01em |
| `text-h3` | 24px | 700 | 1.4 | -0.01em |
| `text-body-lg` | 18px | 400 | 1.6 | normal |
| `text-body` | 16px | 400 | 1.6 | normal |
| `text-body-sm` | 14px | 500 | 1.5 | normal |
| `text-label-caps` | 12px | 700 | 1 | 0.05em |

Family: Manrope (all weights 200–800)

## Spacing Scale

Based on Tailwind defaults (0.25rem increments). Standard component spacing:
- Section gap: `2.5rem` (10)
- Card padding: `1.25rem` (5) / `1.5rem` (6)
- Grid gaps: `1.5rem` (6)
- Inset padding: `1rem` (4) / `1.5rem` (6)

## Border Radius

| Token | Value |
|---|---|
| `--radius-sm` | 0.25rem |
| `--radius` | 0.5rem |
| `--radius-md` | 0.75rem |
| `--radius-lg` | 1rem |
| `--radius-xl` | 1.5rem |
| `--radius-full` | 9999px |

## Animation

### Easing
`cubic-bezier(0.16, 1, 0.3, 1)` — custom ease-out for all transitions.

### Durations
- Micro-interactions (hover, active): 150–200ms
- Component transitions (fade, slide): 250–400ms
- Page transitions: 400–600ms

### Available Triggers (core/animations.ts)
- `fadeIn`, `fadeInUp`, `fadeInDown`, `fadeInLeft`, `fadeInRight`
- `scaleIn`, `bounceIn`
- `slideInRight`, `slideInUp`
- `collapse` (height/opacity)
- `listStagger`, `gridStagger`
- `routeAnimations`
- `cardEnter`
- `pulse`, `shimmerBar`

### Micro-interaction Rules
1. **Hover**: `150ms ease` — transform translateY(-1px) + shadow, or background tint
2. **Active**: `100ms ease` — scale(0.97) on buttons
3. **Focus**: ring 2px primary with 20% opacity
4. **Transition shared**: `background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` (dark mode)

## Component Architecture

```
app/
├── core/          # Singleton services, guards, layouts
├── shared/        # Reusable dumb components
├── features/      # Feature modules (lazy-loaded)
│   ├── auth/      # Login
│   ├── admin/     # Admin dashboard, users, sedes, finanzas, ...
│   ├── therapist/ # Therapist dashboard, sessions, calendar, ...
│   └── patient/   # Patient dashboard, games, progress
```

### Layout Hierarchy
```
<app-admin-layout>         # or therapist-layout, patient-layout
  <app-sidebar />          # Role-filtered navigation
  <div class="layout__main">
    <app-header />         # Title, actions, notifications, user menu
    <div class="layout__content">
      <router-outlet />    # Feature pages
    </div>
    <app-ai-chat />        # Floating Llama copilot
  </div>
</app-admin-layout>
```

## States

Every component must handle:
- **Loading**: Skeleton shimmer or spinner
- **Empty**: Illustration + message + optional CTA
- **Error**: Message + retry button
- **Success**: Toast notification

## Role-Based Views

| Role | Access |
|---|---|
| `admin` | Full system access |
| `supervisor` | Read-only reports, dashboard, sessions (no create/edit/delete) |
| `terapista` | Own sessions, patients, reports |
| `jugador` | Own dashboard, games |

## Dark Mode

Toggle via `<app-sidebar>` footer button. Persisted in localStorage as `theme` key. Applied via `.dark` class on `<html>`.
