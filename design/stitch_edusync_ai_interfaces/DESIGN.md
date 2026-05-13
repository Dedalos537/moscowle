---
name: Institutional Luminary
colors:
  surface: '#f8fbed'
  surface-dim: '#d9dbce'
  surface-bright: '#f8fbed'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f5e7'
  surface-container: '#edefe2'
  surface-container-high: '#e7e9dc'
  surface-container-highest: '#e1e4d7'
  on-surface: '#191d15'
  on-surface-variant: '#43493a'
  inverse-surface: '#2e3229'
  inverse-on-surface: '#f0f2e5'
  outline: '#737968'
  outline-variant: '#c3c9b5'
  surface-tint: '#3e6a00'
  primary: '#3e6a00'
  on-primary: '#ffffff'
  primary-container: '#75a83a'
  on-primary-container: '#1f3800'
  inverse-primary: '#a0d662'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fc'
  on-secondary-container: '#57657a'
  tertiary: '#973a83'
  on-tertiary: '#ffffff'
  tertiary-container: '#dd76c2'
  on-tertiary-container: '#600352'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#bbf37b'
  primary-fixed-dim: '#a0d662'
  on-primary-fixed: '#0f2000'
  on-primary-fixed-variant: '#2e4f00'
  secondary-fixed: '#d5e3fc'
  secondary-fixed-dim: '#b9c7df'
  on-secondary-fixed: '#0d1c2e'
  on-secondary-fixed-variant: '#3a485b'
  tertiary-fixed: '#ffd7ef'
  tertiary-fixed-dim: '#ffade5'
  on-tertiary-fixed: '#3a0031'
  on-tertiary-fixed-variant: '#7a2169'
  background: '#f8fbed'
  on-background: '#191d15'
  surface-variant: '#e1e4d7'
typography:
  h1:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '800'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  h3:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  xs: 0.25rem
  sm: 0.5rem
  md: 1rem
  lg: 1.5rem
  xl: 2.5rem
  gutter: 1.5rem
  container-max: 1280px
---

## Brand & Style
The design system embodies the "Institutional Luminary" direction, projecting an image of academic prestige fused with modern technological intelligence. The aesthetic is rooted in **Corporate Modernism**, emphasizing clarity, organic growth, and stability. 

The UI should evoke a sense of calm authority and limitless potential. High-density information is managed through generous white space and a disciplined adherence to a sophisticated green-centric palette. This style avoids the coldness of traditional institutional software, instead opting for a "living" interface that feels responsive and encouraging for both educators and learners.

## Colors
The palette shifts from cold enterprise blues to a nurturing, growth-oriented green. 

- **Primary Green (#75a83a):** Used for primary actions, progress indicators, and brand-critical accents. It represents vitality and academic advancement.
- **Surface & Background:** The use of white (#ffffff) surfaces against a soft slate background (#f8fafc) creates a subtle "layering" effect that keeps the UI organized without heavy lines.
- **Typography & Neutrals:** Text Dark (#0f172a) is utilized for high-contrast headlines, while Charcoal (#475569) is reserved for body text and secondary labels to reduce visual fatigue during long reading sessions.
- **Functional Colors:** The Error red (#ef4444) is used sparingly to maintain the system's professional composure.

## Typography
Manrope is the sole typeface for this design system, chosen for its geometric purity and excellent legibility in digital environments. 

- **Headlines:** Use tighter letter-spacing and heavier weights (Bold/ExtraBold) to establish a clear information hierarchy.
- **Body Text:** Use regular weights with a generous line height (1.6) to ensure long-form educational content is digestible.
- **Semantic Hierarchy:** Use "Label Caps" for non-interactive metadata and small category tags to provide a distinct visual break from standard body text.

## Layout & Spacing
The system utilizes a **12-column fixed grid** for desktop layouts, transitioning to a fluid model for smaller breakpoints. 

Spacing is governed by an 8px base unit to ensure rhythmic consistency. The layout philosophy prioritizes "breathability"—larger margins (xl) are encouraged between major sections to prevent cognitive overload. Gutters are kept at a standard 24px (lg) to maintain a tight relationship between related content cards while providing enough separation for visual clarity.

## Elevation & Depth
Depth is conveyed through **Ambient Shadows** and **Tonal Layering** rather than heavy borders.

- **The Signature Shadow:** 0 10px 40px rgba(0, 0, 0, 0.03) is applied to primary cards and modals. This creates a soft "lift" off the background, making elements feel light and modern.
- **Surface Tiering:** Use the background color (#f8fafc) for the page canvas and the surface color (#ffffff) for all interactive containers.
- **Interaction Depth:** On hover, shadows should subtly deepen or the element should move 2px upward to provide tactile feedback without breaking the institutional aesthetic.

## Shapes
The shape language is defined by a "Rounded" (0.5rem) base, striking a balance between the friendliness of consumer apps and the structure of institutional tools.

- **Standard Elements:** Buttons, input fields, and small chips use a 0.5rem (8px) radius.
- **Large Containers:** Content cards and modals utilize "rounded-lg" (1rem) or "rounded-xl" (1.5rem) to soften the overall interface.
- **Pills:** Use fully rounded corners for status indicators (e.g., "Active", "Completed") to distinguish them from interactive buttons.

## Components
- **Buttons:** Primary buttons use a solid #75a83a fill with white text. Secondary buttons should use a ghost style with a #e2e8f0 border and Charcoal text.
- **Input Fields:** Use #ffffff background with a 1px #e2e8f0 border. On focus, the border transitions to #75a83a with a soft 2px outer glow of the same color at 10% opacity.
- **Cards:** Cards are the primary vessel for information. They must use the signature shadow and a 1px border of #e2e8f0 only if the shadow is insufficient for accessibility in specific contexts.
- **Chips/Badges:** Use a light tint of the primary color (10% opacity) with the solid #75a83a for text to denote categories or tags.
- **Progress Bars:** Use a rounded track of #e2e8f0 with a #75a83a fill to represent completion, emphasizing the theme of growth.
- **Navigation:** Vertical sidebars should use a clean, white surface with active states indicated by a 4px vertical pill on the left edge in the primary green.