# TruthLens interface design

TruthLens uses a restrained, Linear-inspired dark interface for a careful, evidence-oriented image analysis tool. The canonical reference requested for this project is the Linear entry in [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md/tree/main/design-md/linear.app); this project document records the tokens and usage rules needed by the implementation.

## Color and surfaces

| Token | Value | Use |
|---|---|---|
| canvas | `#010102` | Page background |
| surface | `#0f1011` | Cards |
| surface-raised | `#141516` | Inputs and nested regions |
| surface-hover | `#18191a` | Hovered regions |
| border | `#23252a` | Hairline dividers |
| border-strong | `#34343a` | Emphasized outlines |
| text | `#f7f8f8` | Primary text |
| text-muted | `#d0d6e0` | Supporting text |
| text-subtle | `#8a8f98` | Secondary labels |
| text-tertiary | `#62666d` | Disabled and quiet details |
| accent | `#5e6ad2` | Primary action, focus, selected state |
| accent-hover | `#828fff` | Accent hover |
| success | `#27a644` | REAL result |
| danger | `#e5484d` | FAKE result |
| warning | `#f5a623` | Caution and unavailable states |

Use the lavender accent sparingly. Cards rely on a one-pixel border rather than a strong shadow. A faint accent radial glow is permitted behind the analyzer hero, but avoid other gradients.

## Type and layout

Use Inter at weights 400, 500, and 600; JetBrains Mono is reserved for measurements, identifiers, and file metadata. Set display text to 56px with -1.8px tracking and page headings to 28px with -0.6px tracking. Body text is 16px and captions are 12px. Keep content within 1120px, use a 4px-based spacing rhythm, and leave 24px page gutters on narrow screens.

Buttons use an 8px radius, cards 12px, large panels 16px, and status pills full rounding. Hover and focus transitions last 150–200ms; result reveals may use 300ms. Respect `prefers-reduced-motion`.

## Accessibility

Keep text legible against the dark surfaces, provide a persistent 2px accent focus indicator, use semantic controls and descriptive image text, and announce changing analysis status politely. Never use color alone to convey the model verdict.
