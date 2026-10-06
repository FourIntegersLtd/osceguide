"use client";

import { useState } from "react";
import { Badge, Button, ConfirmModal, Select } from "@/foundation/ui";
import { formatShortDateTime } from "@/foundation/format";
import type { Decision } from "@/domains/assess/results/api";
import { RECRUITMENT_LABEL, RECRUITMENT_OUTCOMES, recruitmentLabel } from "@/domains/assess/results/support";

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
