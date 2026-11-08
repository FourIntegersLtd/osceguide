"use client";

import { useState } from "react";
import { useAssessWords } from "@/capabilities/assess-words";
import { AsyncBoundary, b2bTokens as t } from "@/foundation/ui";
import { PeopleDialog } from "@/domains/assess/ui";
import { boardPill } from "@/domains/assess/results/resultsChrome";
import { useAsync } from "@/foundation/hooks";
import { ResultView } from "@/domains/assess/trainee/ResultView";
import { downloadCandidateResult, readResultPreview } from "@/domains/assess/results/api";
import { errorMessage } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { formatShortDateTime } from "@/foundation/format";
import type { Decision } from "@/domains/assess/results/api";
import {
  ASSESSMENT_OUTCOMES,
  outcomeHint,
  OUTCOME_LABEL,
  RECRUITMENT_LABEL,
  RECRUITMENT_PILLS,
  recruitmentLabel,
  type AssessmentOutcome,
} from "@/domains/assess/results/support";
import { boardInput, boardLabel, boardBtn, boardAlert } from "@/foundation/ui/boardKit";

/** The employer's call on an exam-mode (hire) sitting, as pills. Only the team sees it; the candidate's own view never does. */
export function RecruitmentField({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const w = useAssessWords();
  return (
    <div>
      <label htmlFor="recruitment-outcome" className={`${boardLabel} mb-2`}>
        {w.hiring ? "2. Hiring decision" : "Recruitment outcome (hire only)"}
      </label>
      <select
        id="recruitment-outcome"
        className={boardInput}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Not recorded</option>
        {RECRUITMENT_PILLS.map((outcome) => (
          <option key={outcome} value={outcome}>
            {RECRUITMENT_LABEL[outcome]}
          </option>
        ))}
      </select>
      <div className={`mt-2 ${t.assessMeta}`}>Only your team sees this. Candidates never do.</div>
    </div>
  );
}

/** A released decision: final, so it is read rather than edited. */
export function ReleasedDecision({ decision }: { decision: Decision | null }) {
  const w = useAssessWords();
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-base font-semibold leading-normal">Released</h2>
      <p className={`m-0 ${t.assessMeta}`}>
        {decision?.released_at ? `Released ${formatShortDateTime(decision.released_at)}.` : "Released."}{" "}
        Once released, a decision cannot be edited. Any correction is saved as a new version.
      </p>
      {decision?.recruitment_outcome ? (
        <p className="m-0 text-assess-label">{w.hiring ? "Hiring decision" : "Recruitment outcome"}: {recruitmentLabel(decision.recruitment_outcome)}</p>
      ) : null}
      {decision?.rationale ? <p className="m-0 text-assess-label text-osce-ink-700">{decision.rationale}</p> : null}
    </div>
  );
}

/** Shows staff what the candidate will see of this decision, released or not. Read only, never emails. */
export function ResultPreviewButton({ orgSlug, sittingId, traineeId, label = "Preview what they'll see" }: { orgSlug: string; sittingId: string; traineeId: string; label?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className={boardBtn()} onClick={() => setOpen(true)}>
        {label}
      </button>
      <PeopleDialog open={open} title="Result preview" onClose={() => setOpen(false)}>
        <ResultPreview orgSlug={orgSlug} sittingId={sittingId} traineeId={traineeId} />
      </PeopleDialog>
    </>
  );
}

function ResultPreview({ orgSlug, sittingId, traineeId }: { orgSlug: string; sittingId: string; traineeId: string }) {
  const state = useAsync((signal) => readResultPreview(orgSlug, sittingId, traineeId, signal), [orgSlug, sittingId, traineeId]);
  return (
    <div className="space-y-4">
      <AsyncBoundary state={state}>
        {(result) => (
          <>
            <div className={boardAlert("info")}>
              {result.released_at
                ? "Preview of the released result, as the candidate sees it."
                : "Preview of the last saved version. The candidate cannot see this until it is released."}
            </div>
            <ResultView result={result} />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

/** A released candidate's result as a PDF (the route refuses one that is not released). */
export function ResultPdfButton({ orgSlug, sittingId, traineeId, label = "Download result PDF" }: { orgSlug: string; sittingId: string; traineeId: string; label?: string }) {
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  async function download() {
    setBusy(true);
    setFailure(null);
    try {
      const file = await downloadCandidateResult(orgSlug, sittingId, traineeId);
      saveBlob(file.blob, file.filename);
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button type="button" className={boardBtn()} disabled={busy} onClick={() => void download()}>
        {label}
      </button>
      {failure ? <div role="alert" className={boardAlert("bad")}>{failure}</div> : null}
    </>
  );
}

/** Withdraws a sign-off after a confirm: the decision becomes a draft that has to be signed off again. */
export function ReopenButton({ busy, disabled, onConfirm }: { busy: boolean; disabled: boolean; onConfirm: () => void }) {
  const [confirming, setConfirming] = useState(false);
  return (
    <>
      <button type="button" className={boardBtn()} disabled={disabled || busy} onClick={() => setConfirming(true)}>
        Back to draft
      </button>
      <PeopleDialog
        open={confirming}
        title="Back to draft?"
        lead="The sign-off is removed so you can change the decision. Nothing has been released."
        commitLabel="Back to draft"
        busyLabel="Working…"
        onClose={() => setConfirming(false)}
        onCommit={() => {
          setConfirming(false);
          onConfirm();
        }}
      />
    </>
  );
}

/** Releases signed-off results after a confirm, because it emails the candidates and cannot be undone. */
export function ReleaseButton({
  busy,
  disabled,
  count,
  label,
  onConfirm,
}: {
  busy: boolean;
  disabled: boolean;
  /** How many candidates the release emails. */
  count: number;
  label: string;
  onConfirm: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const who = count === 1 ? "1 candidate" : `${count} candidates`;
  return (
    <>
      <button type="button" className={boardBtn("primary")} disabled={disabled || busy} onClick={() => setConfirming(true)}>
        {label}
      </button>
      <PeopleDialog
        open={confirming}
        title={`Email ${who} their result?`}
        lead="Each can read their outcome as soon as it is released, and a released result is final."
        commitLabel="Release"
        busyLabel="Working…"
        onClose={() => setConfirming(false)}
        onCommit={() => {
          setConfirming(false);
          onConfirm();
        }}
      />
    </>
  );
}

/** The assessment outcome choices; locked once the decision is signed off. */
export function OutcomePicker({ value, disabled, numbered = false, onChange }: { value: AssessmentOutcome | ""; disabled: boolean; /** On a hire exam the result is step 1 of 2. */ numbered?: boolean; onChange: (outcome: AssessmentOutcome) => void }) {
  const w = useAssessWords();
  return (
    <fieldset className="m-0 min-w-0 border-0 p-0" disabled={disabled}>
      <legend className={`${boardLabel} mb-2 p-0`}>{numbered ? "1. Result" : "Outcome"}</legend>
      <div className="grid grid-cols-1 gap-4 min-[901px]:grid-cols-2">
        {ASSESSMENT_OUTCOMES.map((option: AssessmentOutcome) => (
          <button
            key={option}
            type="button"
            aria-pressed={value === option}
            onClick={() => onChange(option)}
            className={`${boardPill(value === option)} disabled:opacity-60`}
          >
            {`${OUTCOME_LABEL[option]} · ${outcomeHint(option, w)}`}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

/** A save was refused because somebody else revised the decision first. */
export function StaleNotice({ onReload }: { onReload: () => void }) {
  return (
    <div role="alert" className={boardAlert("warn")}>
      This decision has changed since you loaded it.{" "}
      <button type="button" className="text-osce-accent underline" onClick={onReload}>
        Load the latest version
      </button>
      <p className="m-0 mt-1">
        Someone else saved a change while you had this open, so yours was not saved. Nothing is lost.
      </p>
    </div>
  );
}
