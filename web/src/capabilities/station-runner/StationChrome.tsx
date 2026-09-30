"use client";

import { useState } from "react";
import { HiOutlineChatBubbleLeftRight, HiOutlineChevronDown, HiOutlineChevronRight } from "react-icons/hi2";
import { LuFlag, LuMessageSquareWarning } from "react-icons/lu";
import { Back, cn, productTokens } from "@/foundation/ui";
import { useToast } from "@/foundation/hooks";
import { flagStation } from "@/capabilities/stations/api";
import type { StationAction } from "@/capabilities/station-runner/useStationAttempt";

export type StationStep = "patient" | "simulation" | "management" | "feedback";

/** The learner's own "come back to" flag on this station, and how to change it. */
export interface ComeBackFlag {
  initial: boolean;
  save: (flagged: boolean) => Promise<void>;
}

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
  flagStationId,
  comeBack,
}: {
  index: number;
  total: number;
  attemptsUsed: number | null;
  attemptLimit: number | null;
  flagStationId?: string | null;
  /**
   * Flagging this station to come back to: the learner's own list, the
   * Flagged tab. The arm supplies it where there is somewhere to keep the
   * flag (a practice set's entry); without it only reporting is offered.
   */
  comeBack?: ComeBackFlag | null;
}) {
  const toast = useToast();
  const [flagged, setFlagged] = useState(false);
  const [marked, setMarked] = useState(comeBack?.initial ?? false);
  const [marking, setMarking] = useState(false);

  const onMark = async () => {
    if (!comeBack || marking) return;
    const next = !marked;
    setMarking(true);
    try {
      await comeBack.save(next);
      setMarked(next);
      toast.show({
        tone: "success",
        title: next ? "Flagged to come back to" : "Flag removed",
        message: next ? "Find it under Flagged stations." : "It is off your Flagged stations.",
      });
    } catch {
      toast.show({
        tone: "error",
        title: "We couldn't change the flag",
        message: "Please try again in a moment.",
      });
    } finally {
      setMarking(false);
    }
  };
  const completed =
    attemptsUsed !== null && attemptLimit !== null && attemptsUsed >= attemptLimit;

  const onFlag = async () => {
    if (!flagStationId) return;
    try {
      await flagStation(flagStationId);
      setFlagged(true);
      toast.show({
        tone: "success",
        title: "Problem reported",
        message: "Thanks. Our team will take a look at this station.",
      });
    } catch {
      toast.show({
        tone: "error",
        title: "We couldn't report this station",
        message: "Please try again in a moment.",
      });
    }
  };

  return (
    <div className="mb-4 flex flex-col gap-4">
      <Back />
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <h1 className={productTokens.b2cPageTitle}>
          {total > 1 ? `Station ${index + 1} of ${total}` : "Station"}
        </h1>
        <div className="flex items-center gap-2">
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
          {comeBack ? (
            <button
              type="button"
              onClick={() => void onMark()}
              disabled={marking}
              aria-pressed={marked}
              aria-label="Flag this station to come back to"
              title={marked ? "Flagged to come back to" : "Flag this station to come back to"}
            >
              <LuFlag
                aria-hidden
                className={cn(
                  "h-4 w-4 transition-colors md:h-5 md:w-5",
                  marked ? "fill-current text-osce-accent" : "text-b2c-text-muted hover:text-osce-accent",
                )}
              />
            </button>
          ) : null}
          {flagStationId ? (
            <button
              type="button"
              onClick={() => void onFlag()}
              aria-pressed={flagged}
              aria-label="Report a problem with this station"
              title="Report a problem with this station"
            >
              <LuMessageSquareWarning
                aria-hidden
                className={cn(
                  "h-4 w-4 transition-colors md:h-5 md:w-5",
                  flagged ? "text-osce-danger" : "text-b2c-text-muted hover:text-osce-danger",
                )}
              />
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** Chips on a wide screen, a select on a narrow one. The old behaviour. */
export function StationTabs({
  steps,
  active,
  onChange,
  feedbackReady = false,
}: {
  steps: StationStep[];
  active: StationStep;
  onChange: (step: StationStep) => void;
  feedbackReady?: boolean;
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
              {step === "feedback" && feedbackReady ? (
                <HiOutlineChatBubbleLeftRight className="h-4 w-4 text-osce-accent" aria-hidden />
              ) : null}
              {step === "feedback" && feedbackReady ? (
                <span className="h-2 w-2 rounded-full bg-osce-success-icon" aria-hidden />
              ) : null}
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
