# LimitIQ v5 interface direction

This directory records the image-first design evidence for the 2026 interface
refresh. The four reference images are generated visual targets, not screenshots
of working functionality. The application remains the source of truth for every
metric and claim.

## Deterministic design selection

- Seed: `160`
- Hero: cinematic center
- Typeface: Outfit
- Components: reviewer-question carousel, inline typography image and horizontal
  governance disclosures
- Motion: scrubbed text reveal and governance-card stacking

## Reference analysis

### Typography

Outfit provides the wide, contemporary editorial voice. Display copy uses tight
tracking, roughly `0.95` line-height and no more than two lines in the hero or
three lines in later chapter headings. Body copy remains generous at 18–22px on
desktop and 16–18px on small screens.

### Colour and contrast

- Midnight navy: `#061722` / `#071923`
- Deep teal: `#007b78`
- Bright teal: `#55d6d1`
- Mist surface: `#f5f8f8`
- Ink: `#102a36`
- Muted text: `#61747d`
- Early warning only: `#f15c4f`

White or bright teal is used against the dark chapters; navy and deep teal are
used on the light chapters. Coral is reserved for material warnings rather than
decoration.

### Layout and spacing

The page follows an attention, interest, desire and action narrative. Chapter
spacing is deliberately large (120–180px desktop), with a maximum readable
width near 72rem. The decision bento is gapless: a seven-column, two-row primary
surface plus two five-column, one-row support surfaces. Controls are rectangular
with restrained corner radii, and there are no nested card stacks.

### Interaction model

The reviewer section rotates real challenge questions rather than fictional
testimonials. Governance disclosures use native `details` and `summary` elements
for keyboard and assistive-technology support. GSAP enhances only the selected
scrubbed text and stacked-card moments. With reduced motion enabled, all content
renders directly in its final state.

### Deliberate departures from the generated references

Generated labels such as “chapter”, “pinned” and numeric section markers are not
implemented because they describe the composition rather than the product.
Generated values are replaced with server-rendered observed, model-estimated or
explicitly simulated values. No generated brand navigation, endorsements or
production-lending claims are copied into the application.

## Files

- `hero-reference.webp`: attention chapter and visual hierarchy
- `interest-reference.webp`: constrained-decision bento
- `desire-reference.webp`: governance chapter and disclosure system
- `action-reference.webp`: reviewer prompts and final action chapter

The production hero artwork is the optimized, text-free
`limitiq/static/hero-risk-horizon.webp` asset.
