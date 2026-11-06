import type { ReactNode } from "react";
import { b2bTokens as t } from "@/foundation/ui";
import { boardChip, type BoardChipTone } from "@/foundation/ui/boardKit";

/**
 * The pieces of the Exams boards (docs/institution-overhaul/boards/Exams.dc.html, NewExam, NewStation)
 * that every authoring list repeats on the organisation arms: text buttons, chips, cards, rows
 * and the page stack at the board's own sizes. The staff console keeps its icon chrome and never
 * reads these. Colours and type come from the assess tokens in foundation/ui.
 */

/** The board's `.chip`. */
export function BoardChip({ tone = "neutral", children }: { tone?: BoardChipTone; children: ReactNode }) {
  return <span className={boardChip(tone)}>{children}</span>;
}

/** The page column of every authoring tab: the board's `.page`. */
export const boardStack = "flex flex-col gap-6";
/** The board's `.meta`. */
export const boardMeta = t.assessMeta;
/** The board's `.acts`. */
export const boardActs = "flex flex-wrap items-center gap-3";
