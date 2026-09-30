"use client";

import { useState } from "react";
import Alert from "@/foundation/forms/Alert";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalHelper,
  ModalPrimaryButton,
  ModalSecondaryButton,
  productTokens,
} from "@/foundation/ui";
import { updateMe } from "@/capabilities/account/api";

/**
 * The retiring client's `AddExamDate` card: a date, a time, and "Save date".
 *
 * The dashboard's calendar pill opens it in a modal, and the setup form shows
 * it on a first visit with "I don't have a date yet" beside the button. The
 * date and the time are stored apart (`exam_date`, `exam_time`); a blank time
 * is saved as no time, which the countdown reads as midnight.
 */
export function AddExamDate({
  examDate: savedDate,
  examTime: savedTime,
  dateLabel,
  onSaved,
  onSkip,
}: {
  examDate: string | null;
  examTime: string | null;
  /** The exam's own noun for this date (`settings.date_label`), e.g. "Interview date". */
  dateLabel: string;
  onSaved?: () => void;
  /** Shown as "I don't have a date yet" when the prompt is optional. */
  onSkip?: () => void;
}) {
  const [examDate, setExamDate] = useState(savedDate ? savedDate.split("T")[0]! : "");
  const [examTime, setExamTime] = useState(savedTime ? savedTime.slice(0, 5) : "");
  const [isUpdating, setIsUpdating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  // "Exam date" -> "Exam time", "Interview date" -> "Interview time".
  const timeLabel = dateLabel.replace(/date$/i, "time");

  const handleSave = async () => {
    if (!examDate) {
      setErrorMessage("Please select an exam date");
      return;
    }
    setIsUpdating(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      await updateMe({ exam_date: examDate, exam_time: examTime ? `${examTime}:00` : null });
      setSuccessMessage("Exam date updated");
      onSaved?.();
    } catch {
      setErrorMessage("Failed to update exam date");
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader className="text-osce-accent-hover">{dateLabel}</B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        <ModalHelper className="mt-0">
          Adding your {dateLabel.toLowerCase()} helps us personalize your study plan and track your
          progress more effectively.
        </ModalHelper>
        {successMessage ? <Alert message={successMessage} type="success" /> : null}
        {errorMessage ? <Alert message={errorMessage} type="error" /> : null}
        <div className="flex flex-col gap-2.5 sm:flex-row">
          <input
            type="date"
            id="examDate"
            aria-label={dateLabel}
            value={examDate}
            onChange={(event) => setExamDate(event.target.value)}
            className={`${productTokens.b2cSettingsFieldInput} flex-1`}
          />
          <input
            type="time"
            id="examTime"
            aria-label={timeLabel}
            value={examTime}
            onChange={(event) => setExamTime(event.target.value)}
            className={`${productTokens.b2cSettingsFieldInput} sm:w-32`}
          />
        </div>
      </B2CPanelCardBody>
      <B2CPanelCardFooter>
        {onSkip ? (
          <ModalSecondaryButton type="button" onClick={onSkip} disabled={isUpdating}>
            I don&apos;t have a date yet
          </ModalSecondaryButton>
        ) : null}
        <ModalPrimaryButton type="button" onClick={() => void handleSave()} disabled={isUpdating}>
          {isUpdating ? "Saving…" : "Save date"}
        </ModalPrimaryButton>
      </B2CPanelCardFooter>
    </B2CPanelCard>
  );
}
