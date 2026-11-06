/**
 * The results screens' board chrome (docs/institution-overhaul/boards/{Results,SittingResults,SlotReview}.dc.html):
 * class strings composed from the shared assess tokens. Pure, so no component repeats a board value.
 */
import { boardCard } from "@/foundation/ui/boardKit";

/** A review card at the assess rhythm (docs/DESIGN.md "Spacing rhythm"): 24px padding, 24px between its parts. */
export const reviewCard = `${boardCard} flex flex-col gap-6 p-6`;
export const boardTileNumber = "mt-1 block text-assess-h2 font-semibold leading-[normal]";
/** The board's `.pill`: an outcome choice; the chosen one carries the quiet selection border. */
export const boardPill = (on: boolean) =>
  `box-border flex min-h-14 items-center rounded-full border px-3 text-left text-assess-meta ${
    on
      ? "border-assess-select-border bg-assess-chip-info-bg text-assess-chip-info-text"
      : "border-osce-border bg-osce-surface text-osce-ink-900"
  }`;
/** The board's `.check` row. */
export const boardCheck = "flex min-h-[61px] items-start gap-2.5 text-assess-label font-normal";
export const boardTile6 = "grid grid-cols-2 gap-3 min-[901px]:grid-cols-6";
