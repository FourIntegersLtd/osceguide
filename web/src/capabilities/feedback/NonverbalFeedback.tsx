"use client";

import { useCallback } from "react";
import { useAsync, useMeEvents } from "@/foundation/hooks";
import { AsyncBoundary, productTokens } from "@/foundation/ui";
import { readNonverbal, type NonverbalRead } from "@/capabilities/attempt-runner/nonverbal/api";
import { formatClock } from "@/capabilities/attempt-runner/useCountdown";

const { b2cCard, b2cSectionTitle } = productTokens;

const MESSAGES: Partial<Record<NonverbalRead["state"], string>> = {
  pending: "Your non-verbal feedback is being prepared.",
  insufficient: "There was not enough clear video to give non-verbal feedback this time. Check your lighting and that your face is in view.",
  failed: "Non-verbal feedback could not be prepared for this consultation.",
};

function Section({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <section className={`${b2cCard} p-4 sm:p-5`}>
      <h2 className={`${b2cSectionTitle} mb-1`}>{heading}</h2>
      {children}
    </section>
  );
}

/** The written section for one read: a status line while it is being prepared, then the summary. */
export function NonverbalSummaryView({ read }: { read: NonverbalRead }) {
  if (!read.supported || read.state === "none") return null;
  const message = MESSAGES[read.state];
  if (message || !read.summary) return <Section heading={read.lingo.heading}><p role="status" className="text-osce-meta leading-relaxed text-b2c-text-muted">{message}</p></Section>;
  const { summary } = read;
  return <Section heading={read.lingo.heading}>
    <p className="mb-3 text-osce-meta text-b2c-text-muted">Based on your camera. Not part of your mark.</p>
    <p className="mb-3 flex flex-wrap gap-x-6 gap-y-1 text-osce-data font-medium tabular-nums text-osce-ink-900">
      <span>Facing the patient {summary.facing_percent}%</span>
      <span>Nods {summary.nods}</span>
    </p>
    <p className="mb-3 text-osce-data leading-relaxed text-osce-ink-900">{summary.summary}</p>
    {summary.strengths.length > 0 && <ul className="mb-3 list-disc space-y-1 pl-5 text-osce-data text-osce-ink-900">
      {summary.strengths.map((s) => <li key={s}>{s}</li>)}
    </ul>}
    {summary.observations.length > 0 && <ul className="flex flex-col gap-3">
      {summary.observations.map((o) => (
        <li key={`${o.at_seconds}-${o.quote}`} className="rounded-osce-md border border-osce-border bg-osce-surface px-3 py-2.5">
          <span className="block text-osce-caption tabular-nums text-b2c-text-muted">{formatClock(o.at_seconds)}</span>
          <span className="block text-osce-meta italic text-b2c-text-secondary">&ldquo;{o.quote}&rdquo;</span>
          <span className="mt-1 block text-osce-data text-osce-ink-900">{o.behaviour}</span>
          <span className="mt-1 block text-osce-meta text-b2c-text-muted">{o.suggestion}</span>
        </li>
      ))}
    </ul>}
  </Section>;
}

/**
 * The candidate's written non-verbal section, shown beside the mark and never part of it. Says
 * what was visibly done and when, in the words being said at the time. Re-reads on the
 * `nonverbal` event while the section is still being written, so it appears without a reload.
 */
export function NonverbalFeedback({ attemptId }: { attemptId: string }) {
  const state = useAsync((signal) => readNonverbal(attemptId, signal), [attemptId]);
  const reload = state.reload;
  useMeEvents(
    state.data?.state === "pending" ? ["nonverbal"] : null,
    useCallback(
      (event) => {
        if (event.name === "resync" || event.data.attempt_id === attemptId) reload();
      },
      [attemptId, reload],
    ),
  );

  return <AsyncBoundary state={state} loading={null} failure={(_error, retry) => <p role="status" className="text-osce-meta text-b2c-text-muted">Non-verbal feedback could not be loaded. <button type="button" onClick={retry} className="underline">Try again</button></p>}>{(read) => <NonverbalSummaryView read={read} />}</AsyncBoundary>;
}
