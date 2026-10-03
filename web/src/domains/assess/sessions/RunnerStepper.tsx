"use client";

import { HiCheckCircle } from "react-icons/hi2";
import type { RunnerStep, StepState } from "@/domains/assess/sessions/support";

/**
 * Where the examination has got to, in four steps.
 *
 * Drawn exactly as the retiring runner drew it. What changed is underneath:
 * every state comes from `runnerSteps` reading the circuit, so the step a
 * supervisor sees is the step the examination is on rather than the step this
 * browser last took part in.
 */
export function RunnerStepper({ steps }: { steps: RunnerStep[] }) {
  return (
    <ol className="flex flex-wrap items-center gap-y-3">
      {steps.map((step, index) => (
        <li key={step.number} className="flex min-w-0 items-center gap-2">
          <Marker number={step.number} state={step.state} />
          <div className="min-w-0">
            <p
              className={`text-osce-caption font-semibold leading-tight ${
                step.state === "idle" ? "text-b2b-icon" : "text-b2b-headline"
              }`}
            >
              {step.label}
            </p>
            <p
              className={`truncate text-osce-caption leading-tight ${
                step.state === "idle" ? "text-b2b-inactive" : "text-b2b-mid"
              }`}
            >
              {step.sublabel}
            </p>
          </div>
          {index < steps.length - 1 ? (
            <div
              className={`ml-1 h-px w-8 shrink-0 sm:w-14 ${
                step.state === "done" ? "bg-b2b-headline" : "bg-b2b-border"
              }`}
              aria-hidden
            />
          ) : null}
        </li>
      ))}
    </ol>
  );
}

function Marker({ number, state }: { number: number; state: StepState }) {
  const tone =
    state === "done"
      ? "border-b2b-headline bg-b2b-headline text-white"
      : state === "active"
        ? "border-b2b-accent bg-b2b-accent text-white"
        : "border-b2b-border bg-b2b-surface text-b2b-icon";

  return (
    <div
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-osce-caption font-bold transition-colors ${tone}`}
    >
      {state === "done" ? <HiCheckCircle className="h-4 w-4" aria-hidden /> : number}
    </div>
  );
}
