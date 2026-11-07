"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { LuCheck, LuChevronRight, LuTriangleAlert } from "react-icons/lu";
import { cn } from "@/foundation/ui/cn";

export type LinkedStep<Id extends string = string> = {
  id: Id;
  label: string;
  note: string;
  /** `attention` was done and needs the reader again. */
  state: "todo" | "attention" | "done";
  /** Where the step is done: a link, or `onSelect` for a step done on this page. No target, no link. */
  href?: string;
  onSelect?: () => void;
};

const MARK = {
  done: "border-transparent bg-osce-success-bg text-osce-success-text",
  attention: "border-transparent bg-osce-warning-bg text-osce-warning-text",
  todo: "border-osce-border bg-osce-surface text-osce-ink-500",
} as const;

const STEP =
  "flex min-h-11 h-full w-full items-center gap-2.5 rounded-control border px-3 py-2 text-left text-assess-meta focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent";

/**
 * One connected stepper for a pipeline: steps joined by chevrons, a check when done, the current step filled
 * with the accent, the rest muted, each step a link (or button) to where it is done. Under it, one hint line
 * and the single primary action (`children`). On a phone the row scrolls sideways instead of clipping.
 * `current` defaults to the first step that is not done.
 */
export function LinkedStepper<Id extends string>({
  steps,
  current,
  hint,
  children,
  label = "Steps",
}: {
  steps: readonly LinkedStep<Id>[];
  current?: Id;
  hint?: string;
  /** The one primary button for the hint. */
  children?: ReactNode;
  label?: string;
}) {
  const now = current ?? steps.find((step) => step.state !== "done")?.id;
  return (
    <div className="flex flex-col gap-3">
      <ol aria-label={label} className="m-0 flex list-none snap-x items-stretch gap-0 overflow-x-auto p-0 pb-1">
        {steps.map((step, index) => {
          const open = step.id === now;
          const mark = (
            <span
              aria-hidden
              className={cn(
                "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-assess-chip font-semibold",
                open ? "border-transparent bg-osce-accent text-white" : MARK[step.state],
              )}
            >
              {step.state === "done" && !open ? (
                <LuCheck className="h-3.5 w-3.5" />
              ) : step.state === "attention" && !open ? (
                <LuTriangleAlert className="h-3.5 w-3.5" />
              ) : (
                index + 1
              )}
            </span>
          );
          const body = (
            <>
              {mark}
              <span className="min-w-0">
                <b className={cn("block text-assess-label font-medium", open ? "text-osce-ink-900" : "text-osce-ink-700")}>{step.label}</b>
                <span className="block truncate text-osce-ink-500" title={step.note}>{step.note}</span>
              </span>
            </>
          );
          const className = cn(
            STEP,
            open ? "border-osce-accent bg-assess-hero-live-bg" : step.state === "done" ? "border-osce-success-bg bg-osce-success-bg" : "border-osce-border bg-osce-surface",
            (step.href || step.onSelect) && "hover:border-osce-accent",
          );
          const current = open ? ("step" as const) : undefined;
          return (
            <li key={step.id} className="flex min-w-[148px] flex-[1_1_0] snap-start items-stretch">
              {step.href ? (
                <Link href={step.href} aria-current={current} className={className}>
                  {body}
                </Link>
              ) : step.onSelect ? (
                <button type="button" aria-current={current} onClick={step.onSelect} className={className}>
                  {body}
                </button>
              ) : (
                <div aria-current={current} className={className}>
                  {body}
                </div>
              )}
              {index < steps.length - 1 ? <LuChevronRight aria-hidden className="mx-1 self-center h-4 w-4 shrink-0 text-osce-ink-500" /> : null}
            </li>
          );
        })}
      </ol>
      {hint || children ? (
        <div role="status" className="flex flex-wrap items-center justify-between gap-3">
          {hint ? <p className="m-0 min-w-0 text-assess-label text-osce-ink-900">{hint}</p> : <span />}
          {children ? <div className="flex shrink-0 items-center gap-2">{children}</div> : null}
        </div>
      ) : null}
    </div>
  );
}
