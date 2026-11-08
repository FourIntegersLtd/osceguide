"use client";

import { ExamClock } from "@/capabilities/attempt-runner";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { reviewStations } from "@/domains/assess/sessions/circuitReviewSteps";
import { heroSummary } from "@/domains/assess/sessions/consoleHero";
import { nowLine } from "@/domains/assess/sessions/turns";
import { phaseLabel } from "@/domains/assess/sessions/support";
import { EndedActions } from "@/domains/assess/sessions/EndedActions";
import { SupervisorControls } from "@/domains/assess/sessions/SupervisorControls";

/**
 * The one thing the console is about: where the circuit is, the server's clock, and the next thing to do.
 * The clock is the server's (`remaining_seconds`); ExamClock only interpolates between pushes.
 */
export function CircuitHero({
  data,
  orgSlug,
  circuitId,
  busy,
  reconnecting,
  failure,
  run,
  onDismissFailure,
  published,
  training = false,
}: {
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  busy: string | null;
  reconnecting: boolean;
  failure: string | null;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
  onDismissFailure: () => void;
  /** The circuit's feedback has been shared: read once by the runner. */
  published: boolean;
  training?: boolean;
}) {
  const w = useAssessWords();
  const circuit = data.circuit;
  const summary = heroSummary(data, w.hiring ? reviewStations(data) : [], w);
  const running = circuit.started_at !== null && circuit.ended_at === null;
  const title = summary.title;
  const detail = training && running && !w.hiring ? nowLine(data) : summary.detail;
  const seconds = circuit.remaining_seconds;
  return (
    <section
      aria-label="Circuit status"
      data-board="controls"
      className="flex flex-col gap-6 rounded-board bg-osce-surface p-6 shadow-sm ring-1 ring-osce-border-light sm:p-8"
    >
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="min-w-0">
          <h2 className="m-0 text-assess-h1 font-semibold text-osce-ink-900">{title}</h2>
          <p className={`${assessMeta} mt-1.5`}>{detail}</p>
        </div>
        {seconds !== null && seconds !== undefined && circuit.ended_at === null ? (
          <span data-clock className="flex flex-col items-end">
            <ExamClock
              plain
              tick
              secondsLeft={seconds}
              label={phaseLabel(circuit.phase)}
              paused={circuit.paused}
              className="text-[56px] font-semibold leading-none tracking-tight tabular-nums text-osce-ink-900"
            />
            <span className={assessMeta}>Timer</span>
          </span>
        ) : null}
      </div>
      {circuit.ended_at !== null ? (
        <EndedActions data={data} published={published} />
      ) : (
      <SupervisorControls
        data={data}
        orgSlug={orgSlug}
        circuitId={circuitId}
        busy={busy}
        reconnecting={reconnecting}
        failure={failure}
        run={run}
        onDismissFailure={onDismissFailure}
        training={training}
      />
      )}
    </section>
  );
}
