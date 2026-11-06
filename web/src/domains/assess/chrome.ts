/**
 * The sitting and console screens' board chrome (docs/institution-overhaul/boards/{Sittings,Sitting,ScheduleSitting,Console}.dc.html):
 * the progress rail step, the card title and the folded rows, as class strings. The card, rows, tabs, chip, buttons and
 * form controls live in `foundation/ui/boardKit`. Pure, so a node test covers it.
 */

/** The board's .st is content-box (110px plus padding and border = 136px border-box). One step of the sitting's progress rail: done is green, the step now due carries a blue border. */
export const boardRailStep = (state: "todo" | "attention" | "done", now: boolean) =>
  `min-w-[136px] flex-[1_1_136px] rounded-board border px-3 py-2.5 text-assess-label ${
    now
      ? "border-assess-select-border bg-assess-hero-live-bg"
      : state === "done"
        ? "border-osce-success-bg bg-osce-success-bg"
        : "border-osce-border-light bg-osce-surface"
  }`;

export const cardTitle = "text-base font-semibold leading-normal text-osce-ink-900";
export const foldSummary =
  "flex min-h-6 cursor-pointer list-none items-center gap-2 border-t border-osce-border-light px-5 py-3.5 text-assess-label font-medium text-osce-ink-900";
export const foldBody = "px-5 pb-4 text-assess-label leading-relaxed text-osce-ink-700";
