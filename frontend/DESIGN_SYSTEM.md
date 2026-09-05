# Nazar frontend design contract

DESIGN.md is the visual source of truth for Nazar.

Read [the root reference](../DESIGN.md) before changing frontend presentation. This file records Nazar's product-specific interpretation. Future features must extend these tokens and primitives, not establish a parallel palette or component language.

## Tokens and typography

`app/globals.css` defines the nine approved colors once in Tailwind v4's `@theme` and exposes semantic surface, border, spacing and layout custom properties. The default Tailwind color palette is disabled. Use named tokens (`text-stone-gray`, `bg-warm-parchment`) or shared classes, not hex values in components. New colors, gradients, shadows and inline visual styles require an explicit design-contract change.

The font stack uses locally installed Inter when present, then the system UI sans-serif. It downloads no fonts and bundles no proprietary files. System fonts may approximate variable weights where unsupported. Headlines use weight 460 with tight tracking; body is 460–500, emphasis 600, and 700 is reserved for small editorial labels. Sizes follow 64px display, 49px major heading, 28px section heading, 16px body, 14px support and 12px captions. Hero/major headings use responsive clamps. Long body copy uses 1.5–1.6 line height for readability rather than the reference's compact UI examples.

Spacing uses a 4px unit and Tailwind's standard spacing scale. `--space-*` aliases avoid redefining Tailwind's numeric spacing tokens (which would change the meaning of existing `p-4`, `mt-4`, etc.). The page is limited to 1200px, with 64–96px major section rhythm, 16px minimum inner padding and 20–32px information-card padding.

## Component hierarchy

`app/components/ui.tsx` provides:

- `PrimaryButton`, `SecondaryButton`: shared action hierarchy and disabled styling.
- `Card`, `SectionHeading`, `NazarInputShell`: surfaces and editorial/input structure.
- `AnalyzerTabs`: typed options, real tab roles, linked panels, roving focus, ArrowLeft/Right and Home/End support.
- `FileDropzone`: shared normal file-picker and drag/drop interaction. Callers retain MIME, size, preview and server-validation logic.
- `ExpandablePanel`: button with aria-expanded/controls and a hidden content region. Closed disclosures reserve no body height.
- `RiskBadge`, `StatusPill`, `SignalChips`: consistent textual risk/status presentation.
- `Notice`, `LoadingStatus`, `Icon`: calm errors, restrained progress and monochrome icons.

Use `.container`, `.section`, `.button-row`, `.form-footer`, `.supporting`, `.caption`, and `.muted` for common page rhythm. Use `Card` for major white surfaces on parchment. Main cards and primary buttons have 16px radii, controls 8px, and chips/pills fully rounded. Small inset metadata rows use the control radius. Depth comes from surfaces and borders, never a drop shadow.

## Button interpretation

The reference's quick-start lilac primary example conflicts with its component section. Nazar resolves this explicitly:

- Primary: Midnight Wine, white text, 16px radius. Analyze, check link, analyze uploads, analyze-and-add and start investigation.
- Secondary: Lilac Mist, charcoal text, subtle charcoal border, 8px radius. Refresh, correction re-analysis and alternate actions.
- Tertiary: transparent controls or links. Royal Violet is reserved for links and reveal affordances; it is never the primary fill or a risk color.

Navigation CTAs use the same `.n-button` classes as button components. Anchor elements remain anchors for navigation; submission actions remain buttons.

## Surfaces and risk

Parchment is the full-page canvas; paper white lifts workspaces and cards. Lilac marks selected tabs and new stages. Deep Lagoon is used only for the full-width investigation narrative band. The footer is Midnight Wine. Hero layers are labelled illustrative product features, never fabricated live results or testimonials.

Risk is always communicated in words and scores: Low risk is neutral; Medium risk uses lilac; High risk uses a wine outline/tint; Critical risk uses solid wine on its badge. No green/yellow/red traffic-light palette is used. Source disagreement has the same neutral intelligence surface as other statuses and does not visually increase danger.

## Information architecture and future features

The landing page follows header → editorial hero → one analyzer workspace → compact Deep Lagoon investigation intro → how-it-works → wine footer. The #investigation address opens a distinct workspace, hiding the landing content. Hash navigation preserves mounted workspaces and drafts, supports back/forward navigation, and moves focus to the destination. Investigation steps reflect creation and evidence count, never inferred attack detection. The start action gives way to evidence guidance after creation; restarting lives in a disclosure. Message, link, screenshot and voice panels stay mounted when hidden so switching tabs retains drafts, results and pending work.

AnalysisCard prioritizes risk, explanation, recommended action and detected signals. Advanced intelligence, official guidance and URLs use disclosures. Keep V4 suspiciousness separate from similarity; never translate it into a percentage chance of fraud. All agreement enums have explicit readable labels. Unavailable ML or AI is an individual source state, not a failed whole analysis.

V13 grounding was detected and integrated through the existing TrustedGuidance component. Empty/unavailable guidance is omitted. Preserve its URL allowlist, explicit reference-link text, `noopener noreferrer` and manual navigation. Suspicious evidence URLs must remain text, never anchors.

Investigation summaries, progression, composer and timeline have separate surfaces. Evidence-specific analysis stays collapsed by default. New stages use labelled lilac chips. Contextual reinforcements quote the backend explanation and identify earlier evidence; do not add them to detected-here signals. Preserve idempotent retries, server error handling and investigation expiry behavior.

For a new feature: define/add its typed API data, place it in the appropriate existing result or investigation region, compose shared primitives, and use only named design tokens. A new advanced result should normally be a disclosure rather than another above-the-fold card.

## Accessibility and responsive behavior

Visible focus rings apply to all interactive elements, with an inset ring on clipped tabs. Native buttons and associated input labels support keyboards. A skip link reaches the analyzer. Risk labels never depend on color. File controls retain the native picker; drag/drop is supplementary. Inputs use 16px text on mobile, disclosures expose state, and reduced motion disables transitions/spinners and smooth scrolling.

At <=1024px, the investigation composer/timeline become one column. At <768px, hero, summaries, intelligence and educational sections stack; progression switches from horizontal to vertical. Tabs stay four compact columns, long evidence wraps, and containers use 16px mobile gutters. Check 375, 768, 1024 and 1440px in a connected browser before declaring visual acceptance.

## Validation

Run `npm run lint`, `npm run build -- --webpack`, `npm run design:check`, and `npm run test:ui`. There was no existing frontend test runner; `test:ui` now checks static React state rendering, accessibility markup, safe links, reinforcement distinctions and upload validation. It does not simulate browser layout or interactions. The design check enforces palette/inline-style/display-weight rules so future components cannot silently restore the old visual system.

Browser discovery during this migration returned no available browser connection. Responsive rules and accessibility relationships were reviewed in code, but visual screenshots, keyboard interaction and live upload flows still need browser verification. Do not describe static or build checks as visual testing.
