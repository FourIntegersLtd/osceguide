"use client";

import { useState } from "react";
import {
  AsyncBoundary,
  ModalHelper,
  ModalPrimaryButton,
  Panel,
  productTokens,
} from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { readMe, updateMe, type Me } from "@/capabilities/account/api";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cSettingsFieldInput, b2cSettingsFieldInputDisabled } = productTokens;

/**
 * How an exam reads on the settings screen.
 *
 * The backend names every exam (`DashboardExam.name` / `ExamRead.name`), an
 * institution's own included, so this is a fallback for the moment before
 * that name has loaded rather than a second source of exam names.
 */
export function examLabel(name: string | null | undefined, code: string | null | undefined): string {
  if (name) return name;
  if (!code) return "";
  return code.toUpperCase();
}

/**
 * Which exam this account is for, and when they sit it.
 *
 * The retiring client's Exam tab: an "Exam" card with the type read-only, and
 * an "Exam date" card that is yours to set, with an optional time of day
 * (`users.exam_time`) beside the date.
 *
 * The exam stays read-only because changing it is not a settings change. It
 * decides which library, which material and which peers a person sees, and
 * moving somebody between exams is a support action against what they have
 * actually bought.
 */
export default function ExamPanel() {
  const state = useAsync((signal) => readMe(signal), []);

  return (
    <SettingsTabShell>
      <AsyncBoundary state={state}>{(me) => <ExamCards key={me.id} me={me} />}</AsyncBoundary>
    </SettingsTabShell>
  );
}

function ExamCards({ me }: { me: Me }) {
  const { codes, name, settings } = useCurrentExam();
  // What they signed up to sit, or — if they have since bought others — what
  // they hold. The old screen fell back to "sca" when nothing was set.
  const code = me.exam_code ?? codes[0] ?? "sca";

  return (
    <>
      <Panel title="Exam">
        <div className="space-y-4">
          <ModalHelper className="mt-0">
            Your exam type and date. These are the same options as on your dashboard.
          </ModalHelper>
          <div>
            <label htmlFor="settings-exam-type" className={b2cFieldLabel}>
              Exam type
            </label>
            <input
              id="settings-exam-type"
              type="text"
              value={examLabel(name, code)}
              disabled
              className={b2cSettingsFieldInputDisabled}
            />
            <p className="mt-1.5 text-osce-meta text-ink-subtle">
              Exam type is set when you signed up. Contact support if you need to switch exams.
            </p>
          </div>
        </div>
      </Panel>

      <ExamDateCard
        initialDate={me.exam_date ?? ""}
        initialTime={(me.exam_time ?? "").slice(0, 5)}
        dateLabel={settings.date_label}
      />
    </>
  );
}

/** The old `AddExamDate` card: date required, time optional, toasts on save. */
function ExamDateCard({
  initialDate,
  initialTime,
  dateLabel,
}: {
  initialDate: string;
  initialTime: string;
  dateLabel: string;
}) {
  const [examDate, setExamDate] = useState(initialDate);
  const [examTime, setExamTime] = useState(initialTime);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");

  const save = async () => {
    setError("");
    setSuccessMessage("");
    if (!examDate) {
      setError("Please select an exam date");
      return;
    }
    setSaving(true);
    try {
      await updateMe({ exam_date: examDate, exam_time: examTime ? `${examTime}:00` : null });
      setSuccessMessage("Exam date updated");
    } catch {
      setError("Failed to update exam date");
    } finally {
      setSaving(false);
    }
  };

  // "Exam date" -> "Exam time", "Interview date" -> "Interview time".
  const timeLabel = dateLabel.replace(/date$/i, "time");

  return (
    <Panel title={dateLabel}>
      <div className="space-y-4">
        <ModalHelper className="mt-0">
          Adding your {dateLabel.toLowerCase()} helps us personalize your study plan and track your
          progress more effectively.
        </ModalHelper>
        {successMessage ? <Alert message={successMessage} type="success" /> : null}
        {error ? <Alert message={error} type="error" /> : null}
        <div className="flex flex-col gap-2.5 sm:flex-row">
          <label htmlFor="settings-exam-date" className="sr-only">
            {dateLabel}
          </label>
          <input
            id="settings-exam-date"
            type="date"
            value={examDate}
            onChange={(event) => setExamDate(event.target.value)}
            className={`${b2cSettingsFieldInput} flex-1`}
          />
          <label htmlFor="settings-exam-time" className="sr-only">
            {timeLabel}
          </label>
          <input
            id="settings-exam-time"
            type="time"
            value={examTime}
            onChange={(event) => setExamTime(event.target.value)}
            className={`${b2cSettingsFieldInput} sm:w-32`}
          />
        </div>
      </div>
      <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
        <ModalPrimaryButton type="button" onClick={() => void save()} disabled={saving}>
          {saving ? "Saving…" : "Save date"}
        </ModalPrimaryButton>
      </div>
    </Panel>
  );
}
