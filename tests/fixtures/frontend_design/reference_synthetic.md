---
name: frontend-design
description: Synthetic reference skill for offline tests. Guides building web interfaces with clear visual hierarchy, deliberate typography, restrained color, and accessibility built in. Written specifically as a redistribution-safe stand-in for license-restricted upstream skill texts.
license: CC0-1.0 (synthetic fixture written for this repository)
---

# Frontend Design

Treat every interface task as a design problem before it becomes a markup
problem. Start from the smallest possible inventory of visual decisions that
make the page feel intentional: a type scale, a spacing rhythm, a restrained
palette, and one idea that makes the result recognizable.

## Establish hierarchy

Decide what the single most important element on each screen is, and spend
contrast there: weight, size, or color intensity. Everything else recedes.
Avoid decorating secondary elements; subtraction usually reads as polish.

- Headings carry structure, not decoration.
- Body text stays between 45 and 75 characters per measure.
- Interactive elements share one consistent affordance style.

## Choose typography deliberately

Pick two families at most. One carries identity, one carries density. Define
a modular scale (for example 1.25x) and refuse sizes outside it. Line height
tightens as size grows; never let long-form reading exceed comfortable line
heights around 1.6.

## Restrained color

Start from a near-neutral surface, one brand hue, and one accent reserved for
actions and state. Verify contrast ratios early rather than at the end:

```bash
npx contrast-checker --ratio 4.5 --foreground "#111" --background "#fafafa"
```

If a section feels visually loud, demote its colors before removing content.

## Layout rhythm

Use a spacing scale with a single base unit. Adjacent related blocks sit
closer than unrelated ones. Full-width bands alternate with contained content
columns so pages breathe instead of tiling edge to edge.

## Distinctive direction

Before writing components, commit to one concrete direction note in a
sentence: the mood, the era it references, and the thing a stranger would
remember afterward. Keep that sentence visible during implementation and
check finished screens against it.

## Accessibility floor

Build the accessible version first: semantic landmarks, visible focus states,
keyboard paths through interactive flows, alt text that conveys purpose.
Run automated checks and manually tab through critical journeys:

## Responsive behavior

Design the narrow case honestly rather than shrinking desktop parts. Let
content reflow; collapse navigation progressively; prefer scroll over tabs on
small screens.

## Motion restraint

Animation explains change or draws attention once. Durations stay short,
easings stay simple, nothing loops without purpose.

## Self-critique pass

Finished work gets one review against the direction note, the hierarchy map,
and the accessibility floor before handoff.

Further reading lives at https://example.com/design-foundations but treat any
external checklist as optional garnish.
