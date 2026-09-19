"use client";

import { HiOutlineChevronDown, HiOutlineChevronRight } from "react-icons/hi2";
import { Back, cn, productTokens } from "@/foundation/ui";
import type { StationAction } from "@/domains/train/station/useStationAttempt";

export type StationStep = "patient" | "simulation" | "management" | "feedback";

/** The four steps, numbered as the retiring client numbered them. */
export const STEP_LABELS: Record<StationStep, string> = {
  patient: "Reading time",
  simulation: "Consultation",
  management: "Management",
  feedback: "Feedback",
};

const STEP_NUMBER: Record<StationStep, string> = {
  patient: "1",
  simulation: "2",
  management: "3",
  feedback: "4",
};

/** Which steps exist. Sitting a station is only steps one and two. */
export function stepsFor(action: StationAction): StationStep[] {
  return action === "review"
    ? ["patient", "simulation", "management", "feedback"]
    : ["patient", "simulation"];
}

/**
 * Where you are in the session, and how many goes you have left.
 *
 * "Station 3 of 8" rather than the station's name, which is the retiring
 * client's and is deliberate: the name gives away the case before it is sat.
 */
export function StationHeader({
  index,
  total,
  attemptsUsed,
  attemptLimit,
}: {
  index: number;
  total: number;
  attemptsUsed: number | null;
  attemptLimit: number | null;
}) {
  const completed =
    attemptsUsed !== null && attemptLimit !== null && attemptsUsed >= attemptLimit;

  return (
    <div className="mb-4 flex flex-col gap-4">
      <Back />
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <h1 className={productTokens.b2cPageTitle}>
          {total > 1 ? `Station ${index + 1} of ${total}` : "Station"}
        </h1>
        {attemptsUsed !== null && attemptLimit !== null && (
          <span className="rounded-full bg-b2c-secondary px-3 py-1 text-osce-body text-b2c-text-secondary">
            {completed ? (
              <span className="font-medium text-osce-success-text">Completed</span>
            ) : (
              <>
                Attempts: {attemptsUsed}/{attemptLimit}
              </>
            )}
          </span>
        )}
      </div>
    </div>
  );
}

/** Chips on a wide screen, a select on a narrow one. The old behaviour. */
export function StationTabs({
  steps,
  active,
  onChange,
}: {
  steps: StationStep[];
  active: StationStep;
  onChange: (step: StationStep) => void;
}) {
  return (
    <>
      <div className="relative mb-4 w-full lg:hidden">
        <label className="sr-only" htmlFor="station-step">
          Step
        </label>
        <select
          id="station-step"
          value={active}
          onChange={(event) => onChange(event.target.value as StationStep)}
          className={cn(
            "w-full cursor-pointer appearance-none rounded-lg border border-b2c-border bg-osce-surface px-4 py-3 pr-12 text-osce-body font-medium text-osce-ink-900 outline-none",
            productTokens.b2cInputFocus,
          )}
        >
          {steps.map((step) => (
            <option key={step} value={step}>
              {STEP_NUMBER[step]}. {STEP_LABELS[step]}
            </option>
          ))}
        </select>
        <HiOutlineChevronDown
          className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-osce-accent"
          aria-hidden
        />
      </div>

      <div className="hidden w-full gap-2 lg:flex">
        {steps.map((step) => (
          <button
            key={step}
            type="button"
            onClick={() => onChange(step)}
            aria-current={active === step ? "step" : undefined}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap rounded-md border px-3 py-2 font-medium transition-all md:px-4",
              active === step
                ? "border-b2c-border bg-osce-surface text-osce-ink-900 shadow-[0_1px_2px_rgba(16,24,40,0.04)]"
                : "border-transparent text-b2c-text-muted hover:bg-osce-surface/70 hover:text-osce-ink-900",
            )}
          >
            <span className="flex items-center gap-4">
              <span
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full font-medium",
                  active === step
                    ? "bg-osce-accent text-white"
                    : "bg-b2c-secondary text-b2c-text-secondary",
                )}
              >
                {STEP_NUMBER[step]}
              </span>
              <span className="font-medium text-osce-ink-900">{STEP_LABELS[step]}</span>
              {(step === "patient" || step === "management") && (
                <HiOutlineChevronRight className="h-4 w-4 text-b2c-text-muted" aria-hidden />
              )}
            </span>
          </button>
        ))}
      </div>
    </>
  );
}
