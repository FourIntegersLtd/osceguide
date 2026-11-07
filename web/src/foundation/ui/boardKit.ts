/**
 * The board kit: the class strings every institution screen draws the same way (card, rows, header row,
 * segmented tabs, chip, rating segment). One copy, here; `domains/assess` and `capabilities/authoring`
 * both import it, so neither reaches into the other. Pure strings with no imports, so a node test loads it.
 * Radii and shadows are tokens (`rounded-board*`, `shadow-board-*` in tailwind.config.ts), never inlined.
 * See docs/DESIGN.md "Board kit".
 */

export type BoardChipTone = "live" | "info" | "warn" | "neutral" | "ok";

/** The board's `.card`. */
export const boardCard = "rounded-panel border border-osce-border bg-osce-surface";
/** A card whose rows must clip to its corners (lists and tables). */
export const boardCardClipped = `${boardCard} overflow-hidden`;
/** The board's `.card.pad` at the sitting rhythm: 20px padding, 14px gap. */
export const boardPad = `${boardCard} flex flex-col gap-3.5 p-5`;
/** The board's `.card.pad` at the authoring and people rhythm: 24px padding, 16px gap. */
export const boardPadWide = `${boardCardClipped} flex flex-col gap-4 p-6`;
/** The board's `.tile`: a count under its name. */
export const boardTile = `${boardCard} p-4`;

/** The board's `.row` at the sitting rhythm (20 by 14). */
export const boardRow =
  "flex flex-wrap items-center gap-4 border-t border-osce-border-light px-5 py-3.5 text-assess-label text-osce-ink-900";
/** The board's `.row` at the authoring rhythm (24 by 16). Ink tokens (`text-ink`) because consoleDesign.test.ts bans `osce-ink-` in authoring screens. */
export const boardRowWide =
  "flex flex-wrap items-center gap-4 border-t border-osce-border-light px-6 py-4 text-assess-label text-ink";
/** The board's `.th` at the sitting rhythm. */
export const boardHeadRow =
  "flex flex-wrap gap-4 bg-osce-surface-inset px-5 py-2.5 text-assess-eyebrow font-normal uppercase text-osce-ink-500";
/** The board's `.th` at the authoring rhythm. */
export const boardHeadRowWide =
  "flex flex-wrap gap-4 bg-osce-surface-inset px-6 py-3 text-assess-eyebrow uppercase text-ink-subtle";

/** The board's `.tabs`: a tinted track holding `boardTab`s. */
export const boardTabs = "inline-flex flex-wrap gap-0.5 self-start rounded-control bg-osce-navActive p-[3px]";
/** One tab in `boardTabs`; the chosen one is a white pill. */
export const boardTab = (on: boolean) =>
  `inline-flex min-h-9 items-center rounded-board-sm px-3.5 text-assess-label ${
    on ? "bg-osce-surface font-medium text-osce-ink-900" : "text-osce-ink-700"
  }`;

/** The board's `.chip`. */
const CHIP = "inline-flex h-6 items-center whitespace-nowrap rounded-full px-2.5 text-assess-chip font-medium";
const ALERT_TONES = {
  warn: "bg-osce-warning-bg text-assess-warn-text",
  info: "bg-assess-chip-info-bg text-assess-chip-info-text",
  ok: "bg-osce-success-bg text-osce-success-text",
  bad: "bg-osce-danger-bg text-osce-danger-text",
} as const;
export type AlertTone = keyof typeof ALERT_TONES;
/** The board's `.al`: a tinted bar whose first line may be bold. */
export const boardAlert = (tone: AlertTone) =>
  `rounded-control px-3.5 py-3 text-assess-label leading-normal ${ALERT_TONES[tone]}`;
const CHIP_TONES: Record<BoardChipTone, string> = {
  live: ALERT_TONES.bad,
  info: ALERT_TONES.info,
  warn: ALERT_TONES.warn,
  ok: ALERT_TONES.ok,
  neutral: "bg-osce-navActive text-osce-ink-700",
};
export const boardChip = (tone: BoardChipTone) => `${CHIP} ${CHIP_TONES[tone]}`;

/** The board's `.seg`: a bordered row of rating choices that clips its corners. */
export const boardSeg = "inline-flex flex-wrap overflow-hidden rounded-control border border-osce-border";
const SEG_CHOICE = "inline-flex min-h-10 items-center border-r border-osce-border px-3.5 text-assess-label last:border-r-0 disabled:opacity-60";
const SEG_TONES = { success: "ok", warning: "warn", danger: "bad", neutral: null } as const;
/** One choice in a `boardSeg`: the chosen one takes the tone of its place in the scale (`ratingVariant`), the rest stay white. */
export function boardSegChoice(selected: boolean, variant: keyof typeof SEG_TONES): string {
  const tone = SEG_TONES[variant];
  if (!selected) return `${SEG_CHOICE} bg-osce-surface`;
  return `${SEG_CHOICE} font-medium ${tone ? ALERT_TONES[tone] : "bg-osce-navActive text-osce-ink-900"}`;
}

const BUTTON =
  "box-border inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control border font-medium disabled:cursor-not-allowed disabled:opacity-60";
const BUTTON_KINDS = {
  default: "border-osce-border bg-osce-surface text-osce-ink-900 [&:not(:disabled)]:hover:bg-osce-canvas",
  primary: "border-osce-accent bg-osce-accent text-white [&:not(:disabled)]:hover:bg-osce-accent-hover",
  danger: "border-osce-border bg-osce-surface text-osce-danger-text [&:not(:disabled)]:hover:bg-osce-canvas",
  warning: "border-osce-border bg-osce-surface text-osce-warning-text [&:not(:disabled)]:hover:bg-osce-canvas",
  ghost: "border-transparent bg-transparent text-osce-ink-900 [&:not(:disabled)]:hover:bg-osce-canvas",
} as const;
type BoardButtonKind = keyof typeof BUTTON_KINDS;

/** The board's `.btn` (44px) and `.btn.sm` (36px, 13px type). */
export function boardBtn(kind: BoardButtonKind = "default", small = false): string {
  const size = small ? "min-h-9 px-3 text-assess-meta !leading-[normal]" : "min-h-11 px-assess-btn text-assess-label";
  return `${BUTTON} ${BUTTON_KINDS[kind]} ${size}`;
}
/** The board's `.btn.sm`, `.btn.sm.ghost` and `.btn.ghost`, as class strings for links and buttons that take one. */
export const boardButtonSmall = boardBtn("default", true);
/** A square icon-only row action (36px, like `.btn.sm`); its name and tooltip come from `RowActions`. */
export function boardIconBtn(tone: "default" | "danger" = "default"): string {
  return `${BUTTON} ${BUTTON_KINDS[tone]} h-9 w-9 shrink-0 !p-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent`;
}

/** The board's `.input`. */
export const boardInput =
  "box-border min-h-11 w-full rounded-control border border-osce-border bg-osce-surface px-3 text-assess-desc text-osce-ink-900";
/** The board's `label`. */
export const boardLabel = "mb-1.5 block text-assess-label font-medium text-osce-ink-900";
/** The board's `.av`. */
export const boardAvatar =
  "flex h-8 w-8 flex-none items-center justify-center rounded-full bg-osce-navActive text-assess-chip font-semibold text-osce-ink-700";

/** The board's `.toggle` (51 by 31) and its `.knob`; green when on, the border grey when off. */
export const boardToggle = (on: boolean) =>
  `box-border flex h-[31px] w-[51px] flex-none rounded-full p-0.5 disabled:cursor-not-allowed disabled:opacity-60 ${
    on ? "justify-end bg-osce-success-solid" : "justify-start bg-osce-border"
  }`;
export const boardKnob = "h-[27px] w-[27px] rounded-full bg-osce-surface shadow-sm";
/** The board's `.cols`: a wide main column beside a 300px rail that wraps under it. */
export const boardCols = "flex flex-wrap items-start gap-6";
export const boardColsMain = "flex min-w-0 flex-[999_1_520px] flex-col gap-6";
export const boardColsRail = "flex flex-[1_1_300px] flex-col gap-6";
/** A rail card: the board's `.card` with 20px padding and a 10px gap. */
export const boardRailCard = `${boardCard} flex flex-col gap-2.5 p-5`;
