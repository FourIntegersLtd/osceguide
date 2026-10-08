"use client";

import { useState } from "react";
import { HiOutlinePaperAirplane } from "react-icons/hi2";
import { Alert, Badge, Button, ConfirmModal, Select } from "@/foundation/ui";
import { formatShortDateTime } from "@/foundation/format";
import type { Decision } from "@/domains/assess/results/api";
import {
  ASSESSMENT_OUTCOMES,
  OUTCOME_HINT,
  OUTCOME_LABEL,
  RECRUITMENT_LABEL,
  RECRUITMENT_OUTCOMES,
  recruitmentLabel,
  type AssessmentOutcome,
} from "@/domains/assess/results/support";

/** The employer's call on an exam-mode (hire) sitting. The candidate's own view never shows it. */
export function RecruitmentField({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <Select
      label="Recruitment outcome"
      hint="Whether you are taking this candidate on. The candidate does not see it."
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">Not recorded</option>
      {RECRUITMENT_OUTCOMES.map((outcome) => (
        <option key={outcome} value={outcome}>
          {RECRUITMENT_LABEL[outcome]}
        </option>
      ))}
    </Select>
  );
}

/** A released decision: final, so it is read rather than edited. */
export function ReleasedDecision({ decision }: { decision: Decision | null }) {
  return (
    <div className="space-y-2">
      <Badge variant="success" dot>Released</Badge>
      <p className="text-osce-caption text-b2b-mid">
        {decision?.released_at ? `Released ${formatShortDateTime(decision.released_at)}.` : "Released."}{" "}
        Once released, a decision cannot be edited. Any correction is saved as a new version.
      </p>
      {decision?.recruitment_outcome ? (
        <p className="text-osce-body text-b2b-headline">
          Recruitment outcome: {recruitmentLabel(decision.recruitment_outcome)}
        </p>
      ) : null}
      {decision?.rationale ? <p className="text-osce-body text-b2b-graphite">{decision.rationale}</p> : null}
    </div>
  );
}

/** Withdraws a sign-off after a confirm: the decision becomes a draft that has to be signed off again. */
export function ReopenButton({ busy, disabled, onConfirm }: { busy: boolean; disabled: boolean; onConfirm: () => void }) {
  const [confirming, setConfirming] = useState(false);
  return (
    <>
      <Button themeType="b2b" variant="secondary" isLoading={busy} disabled={disabled} onClick={() => setConfirming(true)}>
        Back to draft
      </Button>
      <ConfirmModal
        isOpen={confirming}
        title="Back to draft?"
        message="The sign-off is withdrawn and the decision becomes a draft you can change. It has to be signed off again before it can be released."
        confirmText="Back to draft"
        onCancel={() => setConfirming(false)}
        onConfirm={() => {
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
      <Button themeType="b2b" variant="commit" isLoading={busy} disabled={disabled} onClick={() => setConfirming(true)}>
        <HiOutlinePaperAirplane className="h-4 w-4 shrink-0" aria-hidden /> {label}
      </Button>
      <ConfirmModal
        isOpen={confirming}
        title={`Email ${who} their result?`}
        message="Each can read their outcome as soon as it is released, and a released result is final."
        confirmText="Release"
        onCancel={() => setConfirming(false)}
        onConfirm={() => {
          setConfirming(false);
          onConfirm();
        }}
      />
    </>
  );
}

/** The assessment outcome choices; locked once the decision is signed off. */
export function OutcomePicker({ value, disabled, onChange }: { value: AssessmentOutcome | ""; disabled: boolean; onChange: (outcome: AssessmentOutcome) => void }) {
  return (
    <fieldset className="space-y-2" disabled={disabled}>
      <legend className="mb-2 text-osce-meta font-medium text-b2b-headline">Outcome</legend>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {ASSESSMENT_OUTCOMES.map((option: AssessmentOutcome) => (
          <button
            key={option}
            type="button"
            aria-pressed={value === option}
            onClick={() => onChange(option)}
            className={
              value === option
                ? "flex flex-col gap-0.5 rounded-control border border-b2b-headline bg-canvas px-4 py-3 text-left"
                : "flex flex-col gap-0.5 rounded-control border border-b2b-border bg-b2b-surface px-4 py-3 text-left hover:bg-canvas disabled:opacity-60"
            }
          >
            <span className="text-osce-body font-medium text-b2b-headline">{OUTCOME_LABEL[option]}</span>
            <span className="text-osce-meta text-b2b-mid">{OUTCOME_HINT[option]}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}

/** A save was refused because somebody else revised the decision first. */
export function StaleNotice({ onReload }: { onReload: () => void }) {
  return (
    <Alert tone="warning" title="This decision has changed since you loaded it">
      <p>
        Someone else saved a change while you had this open, so yours was not saved. Nothing is lost. Load the latest version and make your change again.
      </p>
      <Button themeType="b2b" variant="secondary" className="mt-2" onClick={onReload}>
        Load the latest version
      </Button>
    </Alert>
  );
}
