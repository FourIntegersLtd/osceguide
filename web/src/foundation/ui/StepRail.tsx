"use client";

import type { ReactNode } from "react";
import { HiCheck } from "react-icons/hi2";

export type RailStep<Id extends string = string> = {
  id: Id;
  label: string;
  /** `attention` was done and needs the reader again. */
  state: "todo" | "attention" | "done";
  note: string;
};

const DOT = {
  done: "border-transparent bg-osce-success-bg text-osce-success-text",
  attention: "border-transparent bg-osce-warning-bg text-osce-warning-text",
  todo: "border-border bg-osce-surface text-ink-subtle",
} as const;

/**
 * A pipeline's steps on one line: a tick when done, amber when it needs the
 * reader again, the open one filled. Without `onSelect` it only shows where
 * things stand.
 */
export function StepRail<Id extends string>({
  steps,
  current,
  onSelect,
}: {
  steps: RailStep<Id>[];
  current?: Id;
  onSelect?: (id: Id) => void;
}) {
  return (
    <ol className="flex flex-wrap items-start gap-x-1 gap-y-3" aria-label="Steps">
      {steps.map((step, index) => {
        const open = step.id === current;
        const dot = (
          <span
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-osce-meta font-semibold ${
              open ? "border-transparent bg-osce-accent text-white" : DOT[step.state]
            }`}
            aria-hidden
          >
            {step.state === "done" && !open ? <HiCheck className="h-4 w-4" /> : index + 1}
          </span>
        );
        const body = (
          <>
            {dot}
            <span className="flex min-w-0 flex-col text-left">
              <span className={`text-osce-meta font-semibold ${open ? "text-ink" : "text-ink-muted"}`}>
                {step.label}
              </span>
              <span className="text-osce-caption text-ink-subtle">{step.note}</span>
            </span>
          </>
        );
        return (
          <li key={step.id} className="flex items-center gap-1">
            {index > 0 ? <span className="hidden h-px w-6 bg-border sm:block" aria-hidden /> : null}
            {onSelect ? (
              <button
                type="button"
                aria-current={open ? "step" : undefined}
                onClick={() => onSelect(step.id)}
                className="flex items-center gap-2 rounded-osce-md px-2 py-1.5 hover:bg-surface-raised focus:outline-none focus:ring-2 focus:ring-osce-accent/20"
              >
                {body}
              </button>
            ) : (
              <span aria-current={open ? "step" : undefined} className="flex items-center gap-2 px-2 py-1.5">
                {body}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

/** Where things stand in one line, and the one thing to do about it. */
export function NextStepBar({
  line,
  working = false,
  children,
}: {
  line: string;
  /** A job is running: the line says what, and a spinner shows it is alive. */
  working?: boolean;
  /** The single primary action, if there is one to take from here. */
  children?: ReactNode;
}) {
  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-3 rounded-osce-lg border border-border bg-surface-raised px-4 py-3"
    >
      <p className="flex min-w-0 items-center gap-2 text-osce-body text-ink">
        {working ? (
          <span
            className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent text-ink-subtle"
            aria-hidden
          />
        ) : null}
        {line}
      </p>
      {children ? <div className="flex shrink-0 items-center gap-2">{children}</div> : null}
    </div>
  );
}

/** The bar above the rail: where things stand, the one action, and every step. */
export function StepGuide<Id extends string>({
  steps,
  current,
  onSelect,
  line,
  working,
  children,
}: {
  steps: RailStep<Id>[];
  current?: Id;
  onSelect?: (id: Id) => void;
  line: string;
  working?: boolean;
  children?: ReactNode;
}) {
  return (
    <>
      <NextStepBar line={line} working={working}>
        {children}
      </NextStepBar>
      <StepRail steps={steps} current={current} onSelect={onSelect} />
    </>
  );
}
