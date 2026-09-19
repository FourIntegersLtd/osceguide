"use client";

import { useCallback, useState } from "react";
import { HiCheckCircle, HiOutlinePaperAirplane } from "react-icons/hi2";
import { Alert, Badge, Button, Spinner, b2bTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import {
  readDecision,
  releaseDecision,
  saveDecision,
  signOffDecision,
  type CandidateReport,
} from "@/domains/assess/results/api";
import {
  ASSESSMENT_OUTCOMES,
  OUTCOME_HINT,
  OUTCOME_LABEL,
  evidenceFor,
  signOffBlockers,
  workflowLabel,
  workflowTone,
  type AssessmentOutcome,
} from "@/domains/assess/results/support";

/**
 * One candidate's outcome: draft, signed off, released.
 *
 * The backend holds the order — a draft cannot be released directly and a
 * released decision is final — and it re-checks at release that the marking
 * the outcome was judged against has not moved since sign-off. This screen
 * sends that evidence, which is what makes the check mean anything.
 */
export function CandidateDecision({
  orgSlug,
  sittingId,
  candidate,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  candidate: CandidateReport;
  onChanged: () => void;
}) {
  const traineeId = candidate.trainee_id;

  const stored = useAsync(async (signal) => {
    if (!traineeId) return null;
    try {
      return await readDecision(orgSlug, sittingId, traineeId, signal);
    } catch (cause) {
      // Nothing recorded yet is the ordinary case, not a failure.
      if (hasCode(cause, "result_not_found")) return null;
      throw cause;
    }
  }, [orgSlug, sittingId, traineeId]);

  if (!traineeId) {
    return (
      <Alert tone="warning">
        This candidate sat the examination but is not on the roster, and a decision is recorded
        against a roster row. Add them to the roster to record one.
      </Alert>
    );
  }

  if (stored.loading) return <Spinner />;
  if (stored.error) return <Alert tone="danger">{errorMessage(stored.error)}</Alert>;

  return (
    <Form
      key={stored.data?.revision ?? 0}
      orgSlug={orgSlug}
      sittingId={sittingId}
      traineeId={traineeId}
      candidate={candidate}
      decision={stored.data}
      onChanged={() => {
        stored.reload();
        onChanged();
      }}
    />
  );
}

type Decision = Awaited<ReturnType<typeof readDecision>>;

function Form({
  orgSlug,
  sittingId,
  traineeId,
  candidate,
  decision,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  traineeId: string;
  candidate: CandidateReport;
  decision: Decision | null;
  onChanged: () => void;
}) {
  const [outcome, setOutcome] = useState(decision?.assessment_outcome ?? "");
  const [rationale, setRationale] = useState(decision?.rationale ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const state = decision?.workflow_state ?? "draft";
  const released = state === "released";
  const signedOff = state === "signed_off";
  const blockers = signOffBlockers({ outcome: outcome || null, rationale });

  const run = useCallback(async (label: string, action: () => Promise<unknown>, said: string) => {
    setBusy(label);
    setFailure(null);
    setNote(null);
    try {
      await action();
      setNote(said);
      onChanged();
    } catch (cause) {
      setFailure(errorMessage(cause instanceof Error ? cause : new Error(String(cause))));
    } finally {
      setBusy(null);
    }
  }, [onChanged]);

  if (released) {
    return (
      <div className="space-y-2">
        <Badge variant="success">Released</Badge>
        <p className="text-osce-caption text-b2b-mid">
          {decision?.released_at ? `Released ${new Date(decision.released_at).toLocaleString()}.` : "Released."}{" "}
          A released decision is final; a correction is a new revision.
        </p>
        {decision?.rationale ? (
          <p className="text-osce-body text-b2b-graphite">{decision.rationale}</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={workflowTone(state)}>{workflowLabel(state)}</Badge>
        {decision ? (
          <span className="text-osce-caption text-b2b-mid">Revision {decision.revision}</span>
        ) : null}
      </div>

      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      {note && !failure ? <Alert tone="success">{note}</Alert> : null}

      <fieldset className="space-y-2" disabled={signedOff}>
        <legend className="text-osce-caption font-medium text-b2b-headline">Outcome</legend>
        <div className="flex flex-wrap gap-2">
          {ASSESSMENT_OUTCOMES.map((value: AssessmentOutcome) => (
            <button
              key={value}
              type="button"
              aria-pressed={outcome === value}
              title={OUTCOME_HINT[value]}
              onClick={() => setOutcome(value)}
              className={
                outcome === value
                  ? "rounded-md border border-b2b-accent bg-b2b-accent px-3 py-1.5 text-osce-caption font-medium text-white"
                  : "rounded-md border border-b2b-border bg-white px-3 py-1.5 text-osce-caption font-medium text-b2b-mid hover:bg-b2b-cream"
              }
            >
              {OUTCOME_LABEL[value]}
            </button>
          ))}
        </div>
        {outcome ? (
          <p className="text-osce-caption text-b2b-mid">{OUTCOME_HINT[outcome as AssessmentOutcome]}</p>
        ) : null}
      </fieldset>

      <label className="block">
        <span className="text-osce-caption font-medium text-b2b-headline">Rationale</span>
        <textarea
          rows={4}
          value={rationale}
          maxLength={4000}
          disabled={signedOff}
          onChange={(event) => setRationale(event.target.value)}
          placeholder="Why this outcome — in the words you would use to a candidate, or to an appeal."
          className={`${b2bTokens.b2bInputBase} mt-1 w-full`}
        />
      </label>

      {!signedOff && blockers.length > 0 ? (
        <Alert tone="warning" title="Before this can be signed off">
          <ul className="list-inside list-disc space-y-1">
            {blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        </Alert>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {!signedOff ? (
          <>
            <Button
              themeType="b2b"
              variant="secondary"
              isLoading={busy === "save"}
              disabled={busy !== null}
              onClick={() =>
                void run(
                  "save",
                  () =>
                    saveDecision(orgSlug, sittingId, traineeId, {
                      assessmentOutcome: outcome || null,
                      rationale: rationale.trim() || null,
                      evidence: evidenceFor(candidate),
                    }),
                  "Draft saved.",
                )
              }
            >
              Save draft
            </Button>
            <Button
              themeType="b2b"
              variant="commit"
              isLoading={busy === "signoff"}
              disabled={busy !== null || blockers.length > 0}
              onClick={() =>
                void run(
                  "signoff",
                  async () => {
                    // Sign-off reads what is stored, so the draft goes first —
                    // otherwise it signs off the previous revision's words.
                    await saveDecision(orgSlug, sittingId, traineeId, {
                      assessmentOutcome: outcome || null,
                      rationale: rationale.trim() || null,
                      evidence: evidenceFor(candidate),
                    });
                    return signOffDecision(orgSlug, sittingId, traineeId);
                  },
                  "Signed off. It is not with the candidate until it is released.",
                )
              }
            >
              <HiCheckCircle className="h-4 w-4 shrink-0" aria-hidden /> Sign off
            </Button>
          </>
        ) : (
          <Button
            themeType="b2b"
            variant="commit"
            isLoading={busy === "release"}
            disabled={busy !== null}
            onClick={() =>
              void run(
                "release",
                () => releaseDecision(orgSlug, sittingId, traineeId, evidenceFor(candidate)),
                "Released. The candidate can read it now.",
              )
            }
          >
            <HiOutlinePaperAirplane className="h-4 w-4 shrink-0" aria-hidden /> Release to the
            candidate
          </Button>
        )}
      </div>

      {signedOff ? (
        <p className="text-osce-caption text-b2b-mid">
          Signed off against the marking as it stood. If a station has been re-marked since,
          releasing is refused and it has to be reviewed and signed off again.
        </p>
      ) : null}
    </div>
  );
}
