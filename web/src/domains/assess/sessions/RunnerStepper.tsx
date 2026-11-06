"use client";

import type { RunnerStep } from "@/domains/assess/sessions/support";
import { boardRailStep } from "@/domains/assess/chrome";

/**
 * Where the examination has got to, in four steps (the Console board's rail).
 *
 * Every state comes from `runnerSteps` reading the circuit, so the step a supervisor sees is the step the
 * examination is on rather than the step this browser last took part in. Done is green; the step now due
 * carries a quiet light-blue border (`--assess-select-border`), never the accent.
 */
export function RunnerStepper({ steps }: { steps: RunnerStep[] }) {
  return (
    <ol className="flex flex-wrap gap-2">
      {steps.map((step) => (
        <li
          key={step.number}
          aria-current={step.state === "active" ? "step" : undefined}
          className={boardRailStep(step.state === "done" ? "done" : "todo", step.state === "active")}
        >
          <b className="block text-sm font-medium">{step.label}</b>
          {step.sublabel}
        </li>
      ))}
    </ol>
  );
}
