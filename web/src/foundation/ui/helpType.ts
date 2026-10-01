import { b2cPanelCardHeader } from "@/foundation/ui/productTokens";

/**
 * The help dock's type roles (see "Help dock" in `docs/DESIGN.md`).
 *
 * Every piece of text in the dock takes one of these, so a title looks the
 * same whether it is an `h3`, a `p` or a `span`, and whichever section it is
 * in. Two families, two sizes, three weights:
 *
 * - Archivo, semibold: titles. Inter: everything else. No mono.
 * - 16px for anything read or pressed, 13px for anything that supports it.
 * - 600 titles, 500 things you press or that label a group, 400 prose.
 *
 * Article and chat markdown follows the same roles in `.helpCompact`
 * (`markdown.module.css`); change the two together.
 */
export const helpType = {
  /** The name in the coloured bar at the top of the dock. */
  barTitle: "font-heading text-osce-body font-semibold leading-snug text-white",
  /** The title of a view or of a block inside it. Works on any tag. */
  title:
    "font-heading text-osce-body font-semibold leading-snug tracking-tight text-osce-ink-900",
  /** The label on a card's header band, and on the transcript's. */
  groupLabel: b2cPanelCardHeader,
  /** The main line of a row or option someone presses. */
  rowTitle: "font-sans text-osce-body font-medium leading-snug text-osce-ink-900",
  /** Running text: answers, chat bubbles, the transcript. Colour is the surface's. */
  prose: "text-osce-body leading-relaxed",
  /** Descriptions, hints, timestamps and status lines under something else. */
  support: "text-osce-meta leading-relaxed text-osce-ink-500",
  /** A text link inside the dock. */
  link: "text-osce-meta font-medium text-osce-accent underline-offset-2 hover:underline",
} as const;
