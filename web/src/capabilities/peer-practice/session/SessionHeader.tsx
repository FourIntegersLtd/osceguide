"use client";

import { HiOutlineArrowRightOnRectangle } from "react-icons/hi2";
import { Button, productTokens } from "@/foundation/ui";
import { phaseLabel, phaseTitle, type RunnerPhase } from "../support/sessionState";
import { formatCountdown } from "../support/examTimers";
import { ReportAbuseButton } from "./SafetyActions";
import { b2cMetric } from "@/foundation/ui/productTokens";

/**
 * The bar across the top of a practice session: which phase, which role, the
 * server's clock for the phase, and the way out.
 *
 * `seconds` is read from the server's `phase_ends_at`; before the clock starts
 * it is the phase's full length, as the retiring header showed it.
 */
export function SessionHeader({
  sessionId,
  role,
  phase,
  stationName,
  seconds,
  onEndSession,
}: {
  sessionId: string;
  role: "doctor" | "patient";
  phase: RunnerPhase;
  stationName: string;
  seconds: number;
  onEndSession: () => void;
}) {
  const caption = phaseLabel(phase);
  const isDoctor = role === "doctor";
  const showReportAbuse = phase === "consultation" || phase === "debrief";

  return (
    <div className="flex-shrink-0 border-b border-osce-border bg-osce-surface">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-3 py-3 sm:px-4 sm:py-4">
        <div className="min-w-0 flex-1">
          <p className={productTokens.b2cMonoEyebrow}>
            Peer practice · You are the {role}
            {!isDoctor ? ` · ${stationName}` : ""}
          </p>
          <h1 className="truncate text-osce-title font-semibold text-osce-ink-900">{phaseTitle(phase)}</h1>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <div className="text-right">
            <p className={productTokens.b2cMonoEyebrow}>{caption}</p>
            <p role="timer" className={b2cMetric}>
              {formatCountdown(seconds)}
            </p>
          </div>
          {showReportAbuse && <ReportAbuseButton sessionId={sessionId} className="flex-shrink-0" />}
          <Button type="button" variant="secondary" onClick={onEndSession} className="shrink-0 gap-1.5">
            <HiOutlineArrowRightOnRectangle className="h-4 w-4" aria-hidden />
            <span>End session</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
