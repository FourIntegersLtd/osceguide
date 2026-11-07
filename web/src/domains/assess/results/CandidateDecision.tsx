"use client";

import { useCallback, useState } from "react";
import { Spinner, b2bTokens as t } from "@/foundation/ui";

import { boardChip, boardInput, boardLabel , boardBtn, boardAlert } from "@/foundation/ui/boardKit";
import { candidateName } from "@/domains/assess/results/support";
import type { ReactNode } from "react";
import { useAsync } from "@/foundation/hooks";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { hasCode } from "@/foundation/platform-client";
import {
  readDecision,
  saveDecision,
  signOffDecision,
  type CandidateReport,
  type Decision,
} from "@/domains/assess/results/api";
import {
  outcomeChoice,
  releasable,
  releaseRefusal,
  signOffBlockers,
  suggestedOutcome,
  workflowLabel,
} from "@/domains/assess/results/support";
import { assessFormStack } from "@/foundation/ui/b2bTokens";
import { decisionBlockers } from "@/domains/assess/results/ranking";
import { candidateProgress } from "@/domains/assess/results/candidateProgress";
import { OutcomePicker, RecruitmentField, ReleasedDecision, ReopenButton, ResultPreviewButton, StaleNotice } from "@/domains/assess/results/DecisionParts";
import { boardRailStep } from "@/domains/assess/chrome";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * One candidate's outcome: draft, signed off, released.
 *
 * The backend holds the order — a draft cannot be released directly and a
 * released decision is final — and it re-checks at release, from the marking
 * itself, that what the outcome was judged against has not moved since sign-off.
 */
export function CandidateDecision({
  orgSlug,
  sittingId,
  candidate,
  hire,
  stations,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  candidate: CandidateReport;
  /** An exam-mode sitting (hire): the decision also records whether the candidate is taken on. */
  hire: boolean;
  /** The candidate's stations, drawn between the progress rail and the form. */
  stations: ReactNode;
  onChanged: () => void;
}) {
  const w = useAssessWords();
  const traineeId = candidate.trainee_id;

  const stored = useAsync(async (signal) => {
    if (!traineeId) return null;
    return readDecision(orgSlug, sittingId, traineeId, signal);
  }, [orgSlug, sittingId, traineeId]);

  if (!traineeId) {
    return (
      <div role="alert" className={boardAlert("warn")}>
        This candidate took the exam but is not on your trainee list. Add them to the list, then record the decision.
      </div>
    );
  }

  if (stored.loading) return <Spinner />;
  if (stored.error) return <div role="alert" className={boardAlert("bad")}>{assessErrorMessage(stored.error, w)}</div>;

  const steps = candidateProgress(candidate);
  const nowId = steps.find((step) => step.state !== "done")?.id;
  const state = stored.data?.workflow_state ?? "draft";
  return (
    <>
      <div className="flex flex-wrap justify-between gap-3">
        <h2 className="text-base font-semibold leading-normal">{`${candidateName(candidate)} · the decision`}</h2>
        {state !== "released" ? (
          <span className={t.assessMeta}>
            <span className={boardChip(state === "signed_off" ? "ok" : "neutral")}>{workflowLabel(state)}</span>
            {stored.data ? ` Revision ${stored.data.revision}` : ""}
          </span>
        ) : null}
      </div>
      <ol aria-label="Steps" className="m-0 flex list-none flex-wrap gap-2 p-0">
        {steps.map((step) => (
          <li key={step.id} className={boardRailStep(step.state, step.id === nowId)}>
            <b className="block text-assess-label font-medium">{step.label}</b>
            {step.note}
          </li>
        ))}
      </ol>
      {stations}
      <Form
        key={stored.data?.revision ?? 0}
        orgSlug={orgSlug}
        sittingId={sittingId}
        traineeId={traineeId}
        hire={hire}
        suggestion={suggestedOutcome(candidate)?.note ?? null}
        decision={stored.data}
        onChanged={() => {
          stored.reload();
          onChanged();
        }}
      />
    </>
  );
}

function Form({
  orgSlug,
  sittingId,
  traineeId,
  hire,
  suggestion,
  decision,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  traineeId: string;
  hire: boolean;
  suggestion: string | null;
  decision: Decision | null;
  onChanged: () => void;
}) {
  const w = useAssessWords();
  const [outcome, setOutcome] = useState(outcomeChoice(decision?.assessment_outcome));
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
    expectedRevision,
  };

  const state = decision?.workflow_state ?? "draft";
  const released = state === "released";
  const signedOff = state === "signed_off";
  const canRelease = releasable({ decision });
  const blockers = signOffBlockers({ outcome: outcome || null, rationale });
  // A hire is never recorded without its reason, even as a draft.
  const hireBlockers = hire ? decisionBlockers({ recruitment, rationale }) : [];

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
      else setFailure(assessErrorMessage(cause, w));
    } finally {
      setBusy(null);
    }
  }, [onChanged]);

  const preview = decision ? <ResultPreviewButton orgSlug={orgSlug} sittingId={sittingId} traineeId={traineeId} /> : null;

  if (released) {
    return (
      <div className="flex flex-col gap-3.5">
        <ReleasedDecision decision={decision} />
        {preview}
      </div>
    );
  }

  return (
    <>
      {failure ? <div role="alert" className={boardAlert("bad")}>{failure}</div> : null}
      {note && !failure ? <div role="status" className={boardAlert("ok")}>{note}</div> : null}
      {stale && !failure ? (
        <StaleNotice
          onReload={() => {
            setStale(false);
            onChanged();
          }}
        />
      ) : null}

      <div className={assessFormStack}>
        <div>
          <OutcomePicker value={outcome} disabled={signedOff} onChange={setOutcome} />
          {suggestion && !signedOff ? <div className={`mt-2 ${t.assessMeta}`}>{suggestion}</div> : null}
        </div>

        {hire ? <RecruitmentField value={recruitment} disabled={signedOff} onChange={setRecruitment} /> : null}

        <div>
          <label htmlFor="decision-rationale" className={`${boardLabel} mb-2`}>
            {recruitment === "hired" ? "Rationale (required for a hire)" : "Rationale"}
          </label>
          <textarea
            id="decision-rationale"
            rows={4}
            value={rationale}
            maxLength={4000}
            disabled={signedOff}
            onChange={(event) => setRationale(event.target.value)}
            placeholder="Why this outcome, in the words you would use to a candidate or an appeal panel."
            className={`${boardInput} min-h-24 py-2.5`}
          />
          {hireBlockers.map((blocker) => (
            <div key={blocker} role="alert" className={`mt-2 ${boardAlert("warn")}`}>
              {blocker}
            </div>
          ))}
        </div>
      </div>

      {!signedOff && blockers.length === 0 ? (
        <div className={t.assessMeta}>Every station marked · a rationale written</div>
      ) : null}

      {!signedOff && blockers.length > 0 ? (
        <div role="alert" className={boardAlert("warn")}>
          <b className="block font-semibold">Before this can be signed off</b>
          {blockers.map((blocker) => (
            <div key={blocker}>{blocker}</div>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-2.5">
        {preview}
        {!signedOff ? (
          <>
            <button
              type="button"
              className={boardBtn()}
              disabled={busy !== null || hireBlockers.length > 0}
              onClick={() =>
                run("save", () => saveDecision(orgSlug, sittingId, traineeId, draft), "Draft saved.")
              }
            >
              Save draft
            </button>
            <button
              type="button"
              className={boardBtn("primary")}
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
              Sign off
            </button>
          </>
        ) : (
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
        )}
      </div>

      {signedOff && !canRelease ? (
        <div role="alert" className={boardAlert("warn")}>Cannot be released: {releaseRefusal("outcome_not_releasable")}.</div>
      ) : null}
      {signedOff && canRelease ? (
        <div className={t.assessMeta}>
          Signed off. Release it from the button at the top of the results, together with any other signed-off results.
        </div>
      ) : null}
      {!signedOff ? (
        <div className={t.assessMeta}>
          Signed off: the form locks, &quot;Back to draft&quot; appears, and &quot;Result PDF&quot; appears once released. Sign-off covers the marks as they were; a re-mark needs a new sign-off. A withheld or inconclusive outcome is never sent.
        </div>
      ) : null}
      {signedOff ? (
        <div className={t.assessMeta}>
          Sign-off covers the marks as they were at the time. If a station is re-marked afterwards, the result must be reviewed and signed off again before it can be released.
        </div>
      ) : null}
    </>
  );
}
