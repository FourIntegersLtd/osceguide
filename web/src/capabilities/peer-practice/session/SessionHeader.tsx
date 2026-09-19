"use client";

import { LuStethoscope } from "react-icons/lu";
import { HiOutlineArrowRightOnRectangle, HiOutlineUser } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { formatElapsed } from "@/capabilities/peer-practice/support/time";

/**
 * Who you are in this session, and how long it has been running.
 *
 * The retiring header showed a countdown it computed in the browser from a
 * single timestamp, in three places, with three different results after a tab
 * switch. `platform-api` owns no phase clock for a peer session, so this shows
 * elapsed time — which is true — rather than a deadline nobody is keeping.
 */
export function SessionHeader({
  role,
  phaseLabel,
  elapsed,
  running,
  onEndSession,
  busy = false,
}: {
  role: string;
  phaseLabel: string;
  elapsed: number;
  running: boolean;
  onEndSession: () => void;
  busy?: boolean;
}) {
  const isDoctor = role === "doctor";

  return (
    <div className="flex-shrink-0 border-b border-b2c-border bg-osce-surface">
      <div className="mx-auto max-w-7xl px-3 py-3 sm:px-4 sm:py-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div className="flex min-w-0 flex-1 items-center gap-3 sm:gap-4">
            <div
              className={`flex-shrink-0 rounded-lg p-2 ${
                isDoctor ? "bg-osce-accent-subtle" : "bg-osce-success-bg"
              }`}
            >
              {isDoctor ? (
                <LuStethoscope className="h-4 w-4 text-osce-accent sm:h-5 sm:w-5" />
              ) : (
                <HiOutlineUser className="h-4 w-4 text-osce-success-text sm:h-5 sm:w-5" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-osce-body font-semibold text-osce-ink-900">
                {phaseLabel}
              </h1>
              <p className="truncate text-osce-body text-b2c-text-secondary">
                Role:{" "}
                <span
                  className={`font-medium capitalize ${
                    isDoctor ? "text-osce-accent" : "text-osce-success-text"
                  }`}
                >
                  {role}
                </span>
              </p>
            </div>
          </div>

          <div className="flex flex-shrink-0 items-center justify-between gap-2 sm:justify-end sm:gap-3">
            <div className="text-center sm:text-right">
              <div className="font-mono text-osce-body font-bold text-osce-danger">
                {formatElapsed(elapsed)}
              </div>
              <div className="text-osce-body text-b2c-text-muted">Elapsed</div>
            </div>
            <Button
              type="button"
              variant="danger"
              size="md"
              onClick={onEndSession}
              disabled={busy || !running}
              className="shrink-0 gap-1 sm:gap-2"
            >
              <HiOutlineArrowRightOnRectangle className="h-4 w-4" />
              <span className="hidden sm:inline">End Session</span>
              <span className="sm:hidden">End</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
