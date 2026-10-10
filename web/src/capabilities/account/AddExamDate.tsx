"use client";

import { useState } from "react";
import Alert from "@/foundation/forms/Alert";
import { ModalSecondaryButton } from "@/foundation/ui";
import { DatePicker } from "@/foundation/ui/DatePicker";
import { updateMe } from "@/capabilities/account/api";

/**
 * Pick the exam day: clicking a day saves it, then `onSaved` runs. No time of
 * day is asked for or kept (`exam_time` is cleared on every save). The
 * dashboard header holds it in a popover, with "Clear date" once one is set;
 * the mock setup shows it on a first visit with "I don't have a date yet".
 */
export function AddExamDate({
  examDate,
  onSaved,
  onSkip,
  allowClear,
}: {
  examDate: string | null;
  onSaved?: (day: string | null) => void;
  /** Shown as "I don't have a date yet" when the prompt is optional. */
  onSkip?: () => void;
  /** Shown as "Clear date" while a date is set. */
  allowClear?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const save = async (day: string | null) => {
    setBusy(true);
    setErrorMessage("");
    try {
      await updateMe({ exam_date: day, exam_time: null });
      onSaved?.(day);
    } catch {
      setErrorMessage("Failed to update exam date");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2">
      {errorMessage ? <Alert message={errorMessage} type="error" /> : null}
      <div className="flex justify-center">
        <DatePicker value={examDate} onChange={(day) => void save(day)} disabled={busy} />
      </div>
      {onSkip || (allowClear && examDate) ? (
        <div className="flex justify-end gap-2">
          {allowClear && examDate ? (
            <ModalSecondaryButton type="button" onClick={() => void save(null)} disabled={busy}>
              Clear date
            </ModalSecondaryButton>
          ) : null}
          {onSkip ? (
            <ModalSecondaryButton type="button" onClick={onSkip} disabled={busy}>
              I don&apos;t have a date yet
            </ModalSecondaryButton>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
