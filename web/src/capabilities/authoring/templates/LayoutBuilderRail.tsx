"use client";

import type { RailStep } from "@/foundation/ui";

/** The board's `.rail`: one box per step, the current one outlined, a finished one green. A step before the current one goes back. */
export function LayoutBuilderRail<Id extends string>({
  steps,
  current,
  onSelect,
}: {
  steps: RailStep<Id>[];
  current: Id;
  onSelect: (id: Id) => void;
}) {
  const currentIndex = steps.findIndex((step) => step.id === current);
  return (
    <ol className="m-0 flex list-none flex-wrap gap-2 p-0">
      {steps.map((step, index) => {
        const now = step.id === current;
        const done = index < currentIndex;
        const tone = now ? "border-osce-accent bg-assess-hero-live-bg" : done ? "border-osce-success-bg bg-osce-success-bg" : "border-osce-border bg-osce-surface";
        return (
          <li key={step.id} className="flex-[1_1_110px]">
            <button
              type="button"
              aria-current={now ? "step" : undefined}
              disabled={index > currentIndex}
              onClick={() => onSelect(step.id)}
              className={`box-border block w-full rounded-osce-md border px-3 py-2.5 text-left text-assess-meta !leading-[normal] text-ink ${tone}`}
            >
              <b className="block text-assess-label font-medium">{step.label}</b>
              {step.note}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
