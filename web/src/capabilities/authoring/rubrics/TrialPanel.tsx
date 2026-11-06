"use client";

import { useId, useState } from "react";
import { Alert, AsyncBoundary, B2CSegmentedTabs, Badge, cn, SectionSearchField, Textarea } from "@/foundation/ui";
import { useAsync, useSearchQuery } from "@/foundation/hooks";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { listTrialCandidates, type TrialCandidate, type TrialMarkRequest } from "@/capabilities/authoring/api";
import { RubricFeedback } from "@/capabilities/feedback";
import type { FeedbackInputs } from "@/capabilities/authoring/rubrics/previewModel";
import type { TrialMarkState } from "@/capabilities/authoring/rubrics/useTrialMark";

type TrialSource = "transcript" | "attempt";

const SAMPLE_TRANSCRIPT = `Doctor: Hello, I'm Dr Patel. What brings you in today?
Patient: I've had a cough for three weeks and I'm getting short of breath.
Doctor: I'm sorry to hear that. Is there anything you're especially worried about?
Patient: My dad had lung cancer, so I'm scared it's that.`;

/**
 * Mark a real conversation against this version before anyone else is.
 *
 * The author pastes a transcript (one "Speaker: words" line per turn) or
 * names an attempt, and the marking model marks it against the saved
 * version; nothing is stored. Progress streams in, and the result is drawn by
 * the same `RubricFeedback` a candidate would get.
 */
export function TrialPanel({
  trial,
  inputs,
  blockedReason,
  onRun,
}: {
  trial: TrialMarkState;
  inputs: FeedbackInputs | null;
  /** Why a trial cannot run right now (the draft has problems), or null. */
  blockedReason: string | null;
  onRun: (body: TrialMarkRequest) => void;
}) {
  const [source, setSource] = useState<TrialSource>("attempt");
  const [transcript, setTranscript] = useState("");
  const [attemptId, setAttemptId] = useState("");
  const inputId = useId();
  const body: TrialMarkRequest = source === "transcript" ? { transcript } : { attempt_id: attemptId.trim() };
  const empty = source === "transcript" ? transcript.trim() === "" : attemptId.trim() === "";
  const snapshot = trial.snapshot;
  return (
    <div className="space-y-3">
      <p className="text-osce-meta font-medium text-ink-muted">Trial source</p>
      <B2CSegmentedTabs
        items={[
          { id: "attempt", label: "An attempt" },
          { id: "transcript", label: "Paste a transcript" },
        ]}
        value={source}
        onChange={setSource}
        compact
        aria-label="Trial source"
      />
      {source === "transcript" ? (
        <>
          <label htmlFor={inputId} className="sr-only">
            Transcript
          </label>
          <Textarea
            id={inputId}
            textareaSize="sm"
            rows={6}
            value={transcript}
            placeholder={SAMPLE_TRANSCRIPT}
            onChange={(event) => setTranscript(event.target.value)}
            className="font-mono"
          />
        </>
      ) : (
        <AttemptPicker attemptId={attemptId} onChoose={setAttemptId} />
      )}
      <div className="flex flex-wrap items-center gap-2">
        <AuthoringButton
          variant="secondary"
          size="sm"
          disabled={empty || blockedReason !== null || trial.running}
          isLoading={trial.running}
          onClick={() => onRun(body)}
        >
          {trial.running ? "Marking…" : "Run trial mark"}
        </AuthoringButton>
        {trial.running ? (
          <AuthoringButton variant="ghost" size="sm" onClick={trial.cancel}>
            Stop
          </AuthoringButton>
        ) : null}
        {snapshot ? <TrialStatus status={snapshot.status} seconds={snapshot.elapsed_seconds} turns={snapshot.turn_count} /> : null}
      </div>
      {blockedReason ? <p className="text-osce-caption text-ink-subtle">{blockedReason}</p> : null}
      {trial.error ? <Alert tone="danger">{trial.error}</Alert> : null}
      {snapshot?.status === "failed" ? <Alert tone="danger">{snapshot.error ?? "The trial could not be marked."}</Alert> : null}
      {inputs ? (
        <div className="rounded-osce-md border border-osce-border bg-osce-canvas p-3">
          <p className="mb-2 text-osce-caption text-ink-subtle">
            Marked by {inputs.result.model_used ?? "the marker"}. Not saved anywhere.
          </p>
          <RubricFeedback rubric={inputs.rubric} result={inputs.result} narrow showAll trainingNote={false} />
        </div>
      ) : null}
    </div>
  );
}

/**
 * Pick one of this scope's own attempts to trial-mark against (R-6), in place
 * of typing an attempt id blind. Scoped and searched on the server exactly as
 * a trial itself scopes `attempt_id` — nothing offered here is later refused
 * as `attempt_not_found` — and the search runs server-side, never filtering
 * a loaded page in the browser.
 */
function AttemptPicker({
  attemptId,
  onChoose,
}: {
  attemptId: string;
  onChoose: (attemptId: string) => void;
}) {
  const scope = useAuthoringScope();
  const [search, setSearch] = useState("");
  const query = useSearchQuery(search);

  const candidates = useAsync(
    (signal) => listTrialCandidates(scope, { search: query, limit: 20 }, signal),
    [scope.base, query],
  );

  return (
    <div className="space-y-2">
      <SectionSearchField
        value={search}
        onChange={setSearch}
        placeholder="Search by candidate or station…"
        ariaLabel="Search attempts to trial-mark"
      />
      <AsyncBoundary state={candidates} empty={{ title: "No marked attempts found." }}>
        {(data) => (
          <div role="radiogroup" aria-label="Attempt" className="max-h-56 divide-y divide-osce-border overflow-y-auto rounded-osce-md border border-osce-border">
            {data.items.map((candidate) => (
              <AttemptRow
                key={candidate.id}
                candidate={candidate}
                selected={candidate.id === attemptId}
                onSelect={() => onChoose(candidate.id)}
              />
            ))}
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}

function AttemptRow({
  candidate,
  selected,
  onSelect,
}: {
  candidate: TrialCandidate;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-osce-meta transition-colors",
        selected ? "bg-osce-accent-subtle" : "hover:bg-osce-canvas",
      )}
    >
      <span className="min-w-0">
        <span className="block truncate font-medium text-ink">{candidate.candidate_label}</span>
        <span className="block truncate text-osce-caption text-ink-subtle">
          {candidate.station_title ?? "Station removed"} · {new Date(candidate.created_at).toLocaleDateString()}
        </span>
      </span>
      <span className="shrink-0 text-osce-caption text-ink-subtle">
        {candidate.turn_count} {candidate.turn_count === 1 ? "turn" : "turns"}
      </span>
    </button>
  );
}

function TrialStatus({ status, seconds, turns }: { status: string; seconds: number; turns: number }) {
  const tone = status === "marked" ? "success" : status === "failed" ? "danger" : "info";
  const word = status === "marked" ? "Marked" : status === "failed" ? "Failed" : "Marking";
  return (
    <Badge tone={tone} size="sm" dot>
      {word} · {Math.round(seconds)} s · {turns} {turns === 1 ? "turn" : "turns"}
    </Badge>
  );
}
