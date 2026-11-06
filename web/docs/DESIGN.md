# Design language

How platform-web looks, and which token to reach for. Carried across from the
retiring client's two Cursor rules (`b2c-design-language.mdc`,
`b2b-design-language.mdc`), corrected to what this app actually does.

Before finishing UI work: look away, look back. The page should feel **alive
but professional**, never bland.

## Two palettes, on purpose

| Palette | Classes | Defined in | Use it for |
|---|---|---|---|
| **Semantic** | `bg-canvas`, `bg-surface`, `text-ink`, `text-ink-muted`, `bg-accent`, `border-border`, `bg-danger-subtle`… | `src/foundation/ui/tokens.css` | **All new code.** Each arm's shell sets `data-surface`, and these re-skin themselves |
| **Product** | `osce-*` (and the older `b2c-*`, `b2b-*`, `landing-*` aliases) | `src/foundation/ui/osceTokens.css` | Ported screens, which keep them so they look exactly as they did |

A literal `bg-blue-600` picks one arm's side and breaks the other skins. The
reasoning is in the header of `tailwind.config.ts`.

### The four skins (`tokens.css`)

| `data-surface` | Feel | Accent | Radius |
|---|---|---|---|
| `train` (default) | The consumer app: osce canvas, calm | blue `#2563EB` | control 8px, panel 12px |
| `assess` | A workspace used all day: denser, cooler, flatter | navy `#1E3A8A` | control 6px, panel 8px |
| `hire` | Assess with the employer's warmer accent | teal `#0D9488` | as assess |
| `platform` | Staff console: same as train | blue | as train |

## Colour

- **Canvas** `#F7F8FA` · **surface** white · **nav active** `#F2F4F7`
- **Borders** `#E4E7EC`, light `#F2F4F7`: 1px hairlines, never dark
- **Ink** `900 #101828` headlines · `700 #344054` body · `500 #667085`
  secondary · `400 #98A2B3` muted
- **Semantic** `success | warning | danger | info`, each with its tints. Never
  raw green/red/amber.
- **Feedback bands** (`osce-band-*`) are for scores only, never chrome.

**No black.** No `border-black`, `text-black` or near-black borders anywhere.
Text is the gray ink scale; borders are light hairlines. This is a standing
product preference, not a default.

## Type scale (`tailwind.config.ts`)

| Token | Size | Use |
|---|---|---|
| `text-osce-micro` | 10 | dense overlay chrome only (video tile pills) |
| `text-osce-caption` | 11 | eyebrows, table headers |
| `text-osce-meta` | 13 | metadata, helper text |
| `text-osce-data` | 14 | table cells |
| `text-osce-body` | **16** | default body. Not 15: iOS Safari zooms any focused input under 16px |
| `text-osce-subheading` / `title` / `heading` | fluid | section titles, page titles, rare hero |
| `text-osce-display-*` | fluid | marketing only |

- Never raw `text-sm` / `text-lg` / `text-[Npx]`.
- **Assess skin (boards win).** The institution boards in `docs/institution-overhaul/boards` are the
  specification, so their literal values have tokens: `text-assess-h1` 28/1.2, `-h2` 24/1.3, `-desc` 16/1.5,
  `-meta` 13/1.5, `-card-title` 26/1.2 (the sign-in card title), `-state-title` 16/normal (a short state card's h2), `-label` 14, `-chip` 12, `-eyebrow` 11 caps `.06em`, `-num` 28 (all fixed, no tracking),
  `max-w-assess-page` 1080, `h-assess-dot` 26, and the class strings `assessPage`, `assessTitle`,
  `assessEyebrow`, `assessCard`, `assessChip*`, `assessButton*`, `assessStep*`, `assessStat*`,
  `assessWhyPanel` in `foundation/ui/b2bTokens.ts`. A screen that has a board uses them; it never writes a raw size.
  `web/e2e/assess/board-*.spec.ts` compares each board with the app and fails past 0.5% pixels.
- **Board kit** (`foundation/ui/boardKit.ts`, pure strings): the one copy of `boardCard`/`boardCardClipped`/`boardPad`,
  `boardRow`/`boardRowWide` and `boardHeadRow`/`boardHeadRowWide` (sitting and authoring rhythms), `boardTabs` + `boardTab(on)`
  (the segmented tab strip: People, Settings, Authoring, Sittings all use it), `boardChip(tone)`, `ALERT_TONES`, `boardSeg*`, and the controls: `boardBtn(kind, small)` (+ `boardButtonSmall`/`boardButtonGhost*`), `boardInput`, `boardLabel`, `boardAvatar`, `boardCardPad`, `boardTile`. Sitting and console chrome that is not shared lives in `domains/assess/chrome.ts`.
  `domains/assess` and `capabilities/authoring` import it from foundation, never from each other. Radii and shadows are
  tokens: `rounded-board-sm` 7, `rounded-board` 9, `rounded-board-lg` 14, `rounded-board-xl` 16, `shadow-board-dialog`,
  `shadow-board-sheet`. The shared `Modal` takes `variant="board"` for the board's `.dlg`; never stack `!` overrides on it.
- Headings are fluid already, so **never pair a token with a responsive
  step-up** (`text-osce-title sm:text-osce-heading` double-scales).
- Fonts: the train surface is Open Sauce for everything, numbers, dates and
  timers included (use `tabular-nums`, never `font-mono`), with Fraunces for the
  train page title only (`font-heading`). **Assess, hire and partner draw the page
  title (h1) in Open Sauce 28px semibold** (the institution boards win over the old
  Fraunces rule; `globals.css`). Mono is kept for ids, codes and emails in staff
  and authoring screens; `src/capabilities/noMono.test.ts` guards the rest.

## Help dock

The Athena dock (`capabilities/help`, plus the transcript and cards it shows
from `foundation/livekit`) has its own small type language, so every section
reads as one panel. The roles are constants in `src/foundation/ui/helpType.ts`;
article and chat markdown follows them in `.helpCompact`
(`markdown.module.css`). Use a role, never a hand-written size and weight.

| Role | Looks like | Use |
|---|---|---|
| `barTitle` | Archivo 16 semibold, white | the name in the coloured bar |
| `title` | Archivo 16 semibold, ink-900 | a view's title, a block's title, an article heading |
| `groupLabel` | Inter 16 medium, secondary ink | a card's header band, the transcript's |
| `rowTitle` | Inter 16 medium, ink-900 | the main line of a row, option or suggested card |
| `prose` | Inter 16 relaxed, colour from the surface | answers, chat bubbles, the transcript |
| `support` | Inter 13 relaxed, ink-500 | descriptions, hints, timestamps, status |
| `link` | Inter 13 medium, accent | a text link |

- **Two families.** Archivo is for titles and nothing else; a title is Archivo
  whether it is an `h3`, a `p` or a `span`. No mono in the dock.
- **Two sizes.** 16 for anything read or pressed, 13 for what supports it. No
  15px prose, no 11px captions.
- **Three weights.** 600 is a title, 500 is something you press or a group
  label, 400 is prose. Semibold Inter does not appear.
- **Ink scale only**: 900 titles, 700 prose, 500 support, 400 placeholders and
  chevrons. No zinc hex values.

## Surfaces, radius, layout

- **Cards are flat**: a 1px border on white over the canvas, no shadow. Only
  floating surfaces (modals, toasts, dropdowns) carry a shadow.
- Radius: `rounded-osce-sm` 6 inputs/chips · `md` 8 buttons · `lg` 10 cards ·
  `xl` 16 modals · `rounded-full` avatars and pills only. Semantic primitives
  use the skin's `--radius-control` / `--radius-panel`.
- Width: `max-w-osce-page` (1200px) for consumer pages, `max-w-osce-narrow`
  (820px) for prose. Institution workspaces are full width.
- The shell owns the page inset. Don't add shell-level padding or
  mobile-nav spacers (`mt-20 lg:mt-0`) in a page.

## Forms

One control surface: `Input` / `getInputClassName()` (`src/foundation/ui/inputStyles.ts`),
with `size` and `invalid`. `focus:outline-none` is always paired with
`focus:ring-2`. Never `focus:ring-0`, which leaves keyboard users no focus
indicator (WCAG 2.4.7). `invalid` sets `aria-invalid` too, so errors are not
colour-only.

## Reading tones

Clinical content is tinted by **stage of the consultation**, so a colour means
the same thing in SCA, PLAB, CASC, Ortho and the institution review view.
Keys are in `b2cReadingTones` (`src/foundation/ui/productTokens.ts`).

| Key | Covers | Hue |
|---|---|---|
| `history` | history taking, ICE, patient story | blue |
| `examination` | findings, investigations | teal |
| `reasoning` | differentials, assessment | violet |
| `management` | plan, medication, treatment | green |
| `safety` | red flags, safety-netting | red |
| `education` | explanation, advice | amber |
| `tip` / `practice` | candidate coaching, never beside stage tones | blue / amber |

**Eliciting** from the patient is `history`; **explaining** to the patient is
`education`. Write `tone="history"`, never a colour name. Do not add a second,
arm-local colour map.

## Spacing rhythm and quiet selection (assess, hire, partner)
Named exceptions where the user's feedback (2026-11-05) overrides the boards; staff console and train are unchanged.
- Rhythm: 8px label to control, 28px between fields, 16px between option cards, 24px between sections, 32px above a footer divider, 24-32px card padding. The constants are `assessForm*`, `assessOptionStack`, `assessFooter` in `b2bTokens.ts`; `boardCardPad`, `boardRow`, `boardTh` in `boardUi.tsx` carry the same scale. A board diff therefore scores higher than it did where the board is tighter.
- `Panel`'s `className` lands on the section, not the body: put `flex`/`gap` in `bodyClassName`, or the gap does nothing (this was the zero-gap New exam wizard).
- Selection and focus: 1px `--assess-select-border` (accent at 28% on white) for a selected card, highlighted row or focused field; focus adds a 3px `--assess-focus-ring` (accent at 16%). Never the saturated accent as a border. `globals.css` ("Assess skin: quiet selection and focus") remaps `.border-osce-accent` and its hover/focus forms inside the assess scopes; filled buttons and round dots are exempt.


Institution dialogs (assess, hire, partner) are one shape, `PeopleDialog` in `domains/assess/ui.tsx`, drawn at the boards' `.dlg`: 24px padding, 14px gap, title `text-assess-desc` (16px) semibold, lead `text-assess-label` (14px) at 1.5 leading in ink-500, then Cancel and the commit right-aligned. No second dialog shape; `team/chrome` no longer has one. Field hints sit under their control (board `.hint`), not above.
Institution home screens (Today, Supervisor home, Now running) use `BoardSection`/`BoardRow` (`domains/assess/dashboard/BoardParts.tsx`); section titles use `text-assess-section` (20px, 1.3 leading). Exceptions are in each board spec header.

## Layout principles

1. **One focal idea per screen**: one primary CTA; demote the rest.
2. **Typography is hierarchy**: eyebrow → page title → description in muted ink.
3. **Quiet surfaces**: white cards on grey canvas; colour comes from chips,
   badges and the accent CTA.
4. **Grouped lists** for settings-style rows.
5. **Metrics** in stat cards, not inline counts.

## Console layout (staff pages)

Staff pages (`domains/platform/*`, `staff-media`, `staff-moderation`,
`staff-growth`) use a dedicated kit in `foundation/ui/PlatformConsole.tsx`,
adapted structurally from eventtz's legacy admin — same colours and fonts,
different spacing and arrangement. Same tokens as everywhere else; no new
palette.

The kit paints with **semantic colours** (`text-ink`, `text-ink-subtle`,
`border-border`, `bg-surface`, `bg-accent-subtle`) and the **`text-osce-*` type
scale**; staff screens compose the kit and carry no raw colour or radius
classes of their own. Queue and list screens (Users, Referral payouts,
Moderation, and the inbox and report screens as they move) use the **quiet
kit**: `B2CPageHeader`, one `B2CHero` with a one-line state headline, `B2CGroupedSection`
rows with a trailing `Badge` as the only colour, and the opened item as a
`QuietCard` (title, subtitle, actions, body; the one wrapper over `B2CPanelCard`); `consoleDesign.test.ts` forbids `Panel`, `RowList`, `StatTile`
and `PlatformPageHeader` in them. `Panel` remains for screens not yet moved —
never the generic `Card`. Tabs are `B2CSegmentedTabs` directly
under a `PlatformPageHeader` (or via `PlatformTabbedScreen`).

- **Shell** (`surfaces/platform/PlatformStaffShell.tsx`, `PlatformSidebar.tsx`):
  a fixed-width sidebar (no user-collapse — that mode stayed on the consumer
  rail, `TrainSidebar.tsx`, because it is a different shell). Content is capped
  at `max-w-[80rem]` so wide screens don't stretch tables.
- **`PlatformPageHeader`**: title inline (not in a banded header), an optional
  `icon` chip, a muted `description`, right-aligned `actions`, and an optional
  `back` link — no more hand-rolled back links per page.
- **`Panel`**: replaces the old `Section` + `Card` pairing. Title, description
  and actions live inside the panel, above a divider; `padding="none"` for a
  full-bleed `RowList` body.
- **`RowList` / `Row` / `RowLink`**: list rows at `px-5 py-3.5 sm:px-6`.
  `RowLink` adds the hover tint and trailing chevron for a row that navigates.
- **`StatGrid` / `StatTile`**: a `gap-3 sm:grid-cols-2 lg:grid-cols-4` KPI row —
  uppercase micro-label, `tabular-nums` value, tinted icon chip. The setup assistant's board tiles
  (white card, 13px label, 28px semibold sans number) use `assessStat*` instead.
- **`DetailLayout` / `ActionRail`**: a two-column detail page,
  `lg:grid-cols-[minmax(0,1fr)_20rem]`, with a sticky action rail on the right
  (destructive action last, behind a divider).
- **`EmptyPanel`**: a dashed-border empty state.

`domains/platform/chrome.tsx` now holds only `StatusBadge` and
`WriteOnlyNote` — domain vocabulary that doesn't belong in a generic kit.
Every staff screen imports layout pieces from `foundation/ui` directly.

## Components to reuse (`src/foundation/ui`)

| Use | For |
|---|---|
| `Card`, `Button`, `ButtonLink`, `TextLink`, `Badge`, `Input` | the primitives, built on semantic tokens |
| `PageHeader`, `PlatformPageHeader`, `B2CPageHeader` | page titles |
| `B2CGroupedList` | settings-style navigation |
| `B2CSegmentedTabs`, `PlatformTabbedScreen` | page-level tabs |
| `EmptyState`, `B2CEmptyState`, `B2CSkeleton`, `AsyncBoundary`, `Spinner` | empty, loading and failed states |
| `Modal`, `ConfirmModal`, toast | floating surfaces |
| `DatePicker` | picking one day (react-day-picker painted with tokens); `dateDay.ts` converts `YYYY-MM-DD` without shifting the day |
| `B2BIconChip` (`capabilities/authoring/structure/b2b/components/ui`) | tinted icon squares |

## Do / don't

| Do | Don't |
|---|---|
| Semantic tokens in new code | Raw Tailwind palette (`bg-blue-600`, `gray-*`) |
| `text-osce-*` for every size | `text-sm`, `text-[15px]` |
| Gray ink, light hairlines | Black text or dark borders |
| Flat cards, 1px border | Shadows on cards |
| `focus:ring-2` with `outline-none` | `focus:ring-0` |
| `tone="safety"` | `bgColor="red"` |
| One accent primary per view | Several competing full-width primaries |
