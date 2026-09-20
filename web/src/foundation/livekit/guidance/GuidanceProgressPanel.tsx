"use client";

import { createPortal } from "react-dom";
import { useEffect, useState } from "react";
import { cn } from "@/foundation/ui/cn";
import {
  b2cModalOverlayRoot,
  b2cModalPanel,
  b2cModalPanelBody,
} from "@/foundation/ui/Modal";
import { b2cTokens } from "./tokens";
import {
  PROGRESS_STEP_ACTING,
  PROGRESS_STEP_CAPTURING,
  PROGRESS_STEP_READING,
  type GuidanceProgressStep,
} from "./contracts";
import { uiGuidanceIgnoreProps } from "./captureExclusion";

/**
 * What Athena is doing, while she does it.
 *
 * The wait has two halves and only one of them can be narrated: speech stops the
 * moment the screenshot tool returns, which is exactly when the model starts
 * reading the image. This panel spans both, so the pause never reads as a
 * dropped call. It is deliberately central rather than a line of status text —
 * at the edge of the screen it was missed.
 *
 * It only ever covers the page while there is nothing to point at yet: the agent
 * clears it as it starts to speak, which is the same moment the pointer lands.
 *
 * It wears the shared modal's chrome (`b2cModalOverlayRoot` / `b2cModalPanel` /
 * `b2cModalPanelBody`) but deliberately not the `Modal` component itself. Modal
 * is a dialog: it traps focus, locks app scroll and lays a scrim over the page.
 * All three are wrong here — this thing announces rather than asks, it must not
 * take focus from a live consultation, the agent's own scroll action runs while
 * it is up, and the page underneath is what she is about to point at. It also
 * has to carry `uiGuidanceIgnoreProps`, or it lands in the screenshot she reads.
 */

type Props = {
  step: GuidanceProgressStep | null;
  /** What the agent is acting on, when it said. */
  label?: string | null;
  zIndex?: number;
};

const STEPS: { id: GuidanceProgressStep; title: string }[] = [
  { id: PROGRESS_STEP_CAPTURING, title: "Looking at your screen" },
  { id: PROGRESS_STEP_READING, title: "Finding what you need" },
  { id: PROGRESS_STEP_ACTING, title: "Showing you where" },
];

/** If `done` never arrives — a dropped agent, a crashed tool — do not sit there forever. */
const STALE_AFTER_MS = 30_000;

export function GuidanceProgressPanel({ step, label, zIndex = 2147482900 }: Props) {
  // The step this panel has given up waiting on, rather than a flag that has to
  // be cleared again on every change.
  const [abandoned, setAbandoned] = useState<GuidanceProgressStep | null>(null);

  useEffect(() => {
    if (!step) return;
    const timer = window.setTimeout(() => setAbandoned(step), STALE_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [step]);

  if (typeof document === "undefined" || !step || abandoned === step) return null;

  const activeIndex = STEPS.findIndex((candidate) => candidate.id === step);
  if (activeIndex === -1) return null;

  return createPortal(
    <div
      // `zIndex` overrides the z-[100] baked into the overlay root: the guidance
      // layer sits above app chrome, just under the pointer overlay (2147483000).
      className={cn(b2cModalOverlayRoot, "pointer-events-none")}
      style={{ zIndex }}
      role="status"
      aria-live="polite"
      {...uiGuidanceIgnoreProps}
    >
      <div
        className={cn(
          b2cModalPanel,
          "w-[min(100%,calc(100vw-1rem))] md:w-[360px] md:max-w-[calc(100vw-2rem)]",
        )}
      >
        <div className={b2cModalPanelBody}>
          <ol className="m-0 flex list-none flex-col gap-3 p-0">
            {STEPS.map((entry, index) => (
              <StepRow
                key={entry.id}
                title={entry.id === step && label ? `${entry.title}: ${label}` : entry.title}
                state={index < activeIndex ? "done" : index === activeIndex ? "active" : "pending"}
              />
            ))}
          </ol>
        </div>
      </div>
      <style>{KEYFRAMES}</style>
    </div>,
    document.body,
  );
}

type StepState = "done" | "active" | "pending";

function StepRow({ title, state }: { title: string; state: StepState }) {
  return (
    <li className="flex items-center gap-3 text-osce-body">
      <Marker state={state} />
      <span
        style={{
          color: state === "pending" ? b2cTokens.textMuted : b2cTokens.textPrimary,
          fontWeight: state === "active" ? 600 : 400,
        }}
      >
        {title}
      </span>
    </li>
  );
}

function Marker({ state }: { state: StepState }) {
  if (state === "done") {
    return (
      <span
        className="flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full"
        style={{ background: b2cTokens.primary }}
        aria-hidden
      >
        <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
          <path d="M2.5 6.2 4.8 8.5 9.5 3.8" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  }

  if (state === "active") {
    return (
      <span
        className="ui-guidance-step-active h-[18px] w-[18px] shrink-0 rounded-full"
        style={{ border: `2px solid ${b2cTokens.primary}` }}
        aria-hidden
      />
    );
  }

  return (
    <span
      className="h-[18px] w-[18px] shrink-0 rounded-full"
      style={{ border: `2px solid ${b2cTokens.borderLight}` }}
      aria-hidden
    />
  );
}

const KEYFRAMES = `
@keyframes ui-guidance-step-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(0.82); }
}
.ui-guidance-step-active { animation: ui-guidance-step-pulse 1.4s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) {
  .ui-guidance-step-active { animation: none; }
}
`;
