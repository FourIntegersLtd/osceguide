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
  type Decision,
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
import { RecruitmentField, ReleasedDecision, ReopenButton } from "@/domains/assess/results/DecisionParts";

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
  hire,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  candidate: CandidateReport;
  /** An exam-mode sitting (hire): the decision also records whether the candidate is taken on. */
  hire: boolean;
  onChanged: () => void;
}) {
  const traineeId = candidate.trainee_id;

  const stored = useAsync(async (signal) => {
    if (!traineeId) return null;
    return readDecision(orgSlug, sittingId, traineeId, signal);
  }, [orgSlug, sittingId, traineeId]);

  if (!traineeId) {
    return (
      <Alert tone="warning">
        This candidate took the exam but is not on your trainee list. Add them to the list, then record the decision.
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
      hire={hire}
      decision={stored.data}
      onChanged={() => {
        stored.reload();
        onChanged();
      }}
    />
  );
}

function Form({
  orgSlug,
  sittingId,
  traineeId,
  candidate,
  hire,
  decision,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  traineeId: string;
  candidate: CandidateReport;
  hire: boolean;
  decision: Decision | null;
  onChanged: () => void;
}) {
  const [outcome, setOutcome] = useState(decision?.assessment_outcome ?? "");
  const [recruitment, setRecruitment] = useState(decision?.recruitment_outcome ?? "");
  const [rationale, setRationale] = useState(decision?.rationale ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [stale, setStale] = useState(false);

  // What this screen last read, so a save cannot quietly supersede somebody
  // else's. `decision` is re-read by the parent after every successful write,
  // and this component is keyed on its revision.
  const expectedRevision = decision?.revision ?? 0;
  const draft = {
    assessmentOutcome: outcome || null,
    recruitmentOutcome: hire ? recruitment || null : null,
    rationale: rationale.trim() || null,
    evidence: evidenceFor(candidate),
    expectedRevision,
  };

  const state = decision?.workflow_state ?? "draft";
  const released = state === "released";
  const signedOff = state === "signed_off";
  const blockers = signOffBlockers({ outcome: outcome || null, rationale });

  const run = useCallback(async (label: string, action: () => Promise<unknown>, said: string) => {
    setBusy(label);
    setFailure(null);
    setNote(null);
    setStale(false);
    try {
      await action();
      setNote(said);
      onChanged();
    } catch (cause) {
      // A refused save says the copy on screen is not the newest, which is a
      // different thing to say from "your request failed": the words typed
      // here are still worth keeping, and the latest revision has to be loaded
      // before another save can go through.
      if (hasCode(cause, "decision_revised")) setStale(true);
      else setFailure(errorMessage(cause instanceof Error ? cause : new Error(String(cause))));
    } finally {
      setBusy(null);
    }
  }, [onChanged]);

  if (released) return <ReleasedDecision decision={decision} />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={workflowTone(state)} dot>{workflowLabel(state)}</Badge>
        {decision ? (
          <span className="text-osce-caption text-b2b-mid">Revision {decision.revision}</span>
        ) : null}
      </div>

      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      {note && !failure ? <Alert tone="success">{note}</Alert> : null}
      {stale && !failure ? (
        <Alert tone="warning" title="This decision has changed since you loaded it">
          <p>
            Someone else saved a change while you had this open, so yours was not saved. Nothing is lost. Load the latest version and make your change again.
          </p>
          <Button
            themeType="b2b"
            variant="secondary"
            className="mt-2"
            onClick={() => {
              setStale(false);
              onChanged();
            }}
          >
            Load the latest version
          </Button>
        </Alert>
      ) : null}

      <fieldset className="space-y-2" disabled={signedOff}>
        <legend className="mb-2 text-osce-meta font-medium text-b2b-headline">Outcome</legend>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {ASSESSMENT_OUTCOMES.map((value: AssessmentOutcome) => (
            <button
              key={value}
              type="button"
              aria-pressed={outcome === value}
              onClick={() => setOutcome(value)}
              className={
                outcome === value
                  ? "flex flex-col gap-0.5 rounded-control border border-b2b-headline bg-canvas px-4 py-3 text-left"
                  : "flex flex-col gap-0.5 rounded-control border border-b2b-border bg-b2b-surface px-4 py-3 text-left hover:bg-canvas disabled:opacity-60"
              }
            >
              <span className="text-osce-body font-medium text-b2b-headline">{OUTCOME_LABEL[value]}</span>
              <span className="text-osce-meta text-b2b-mid">{OUTCOME_HINT[value]}</span>
            </button>
          ))}
        </div>
      </fieldset>

      {hire ? <RecruitmentField value={recruitment} disabled={signedOff} onChange={setRecruitment} /> : null}

      <label className="block">
        <span className="text-osce-meta font-medium text-b2b-headline">Rationale</span>
        <textarea
          rows={4}
          value={rationale}
          maxLength={4000}
          disabled={signedOff}
          onChange={(event) => setRationale(event.target.value)}
          placeholder="Why this outcome, in the words you would use to a candidate or an appeal panel."
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
                run("save", () => saveDecision(orgSlug, sittingId, traineeId, draft), "Draft saved.")
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
                run(
                  "signoff",
                  async () => {
                    // Sign-off reads what is stored, so the draft goes first —
                    // otherwise it signs off the previous revision's words.
                    await saveDecision(orgSlug, sittingId, traineeId, draft);
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
          <>
            <ReopenButton
              busy={busy === "reopen"}
              disabled={busy !== null}
              onConfirm={() =>
                // Saving a signed-off decision records a new draft revision; the
                // server refuses it only once the decision is released.
                void run(
                  "reopen",
                  () => saveDecision(orgSlug, sittingId, traineeId, draft),
                  "Back to draft. Change what you need, then sign off again.",
                )
              }
            />
            <Button
              themeType="b2b"
              variant="commit"
              isLoading={busy === "release"}
              disabled={busy !== null}
              onClick={() =>
                run(
                  "release",
                  () => releaseDecision(orgSlug, sittingId, traineeId, evidenceFor(candidate)),
                  "Released. The candidate can read it now.",
                )
              }
            >
              <HiOutlinePaperAirplane className="h-4 w-4 shrink-0" aria-hidden /> Release to the
              candidate
            </Button>
          </>
        )}
      </div>


      {signedOff ? (
        <p className="text-osce-caption text-b2b-mid">
          Sign-off covers the marks as they were at the time. If a station is re-marked afterwards, the result must be reviewed and signed off again before it can be released.
        </p>
      ) : null}
    </div>
  );
}
