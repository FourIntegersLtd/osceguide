"use client";

import { useState } from "react";
import { AsyncBoundary, Button, Input, Panel } from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { readMe, updateMe, type Me } from "@/capabilities/account/api";
import { examLabel, NO_EXAM_LABEL } from "@/capabilities/account/settings/examLabel";
import { settingsMeta } from "@/capabilities/account/settings/SettingsKit";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

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
  // they hold. With neither, the label says so rather than inventing one.
  const code = me.exam_code ?? codes[0];

  return (
    <>
      <Panel title="Exam">
        <Input
          label="Exam type"
          name="examType"
          value={examLabel(name, code) ?? NO_EXAM_LABEL}
          disabled
          readOnly
        />
      </Panel>

      <ExamDateCard
        initialDate={me.exam_date ?? ""}
        initialTime={(me.exam_time ?? "").slice(0, 5)}
        dateLabel={settings.date_label}
      />
    </>
  );
}

/** The date card: date required to save, time optional, or no date at all. */
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
  const [clearing, setClearing] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");

  const save = async () => {
    setError("");
    setSuccessMessage("");
    if (!examDate) {
      setError(`Choose your ${dateLabel.toLowerCase()} first.`);
      return;
    }
    setSaving(true);
    try {
      await updateMe({ exam_date: examDate, exam_time: examTime ? `${examTime}:00` : null });
      setSuccessMessage(`${dateLabel} updated`);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  /** No date yet: the countdown and the pacing stop until one is set. */
  const clear = async () => {
    setError("");
    setSuccessMessage("");
    setClearing(true);
    try {
      await updateMe({ exam_date: null, exam_time: null });
      setExamDate("");
      setExamTime("");
      setSuccessMessage(`${dateLabel} cleared`);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setClearing(false);
    }
  };

  // "Exam date" -> "Exam time", "Interview date" -> "Interview time".
  const timeLabel = dateLabel.replace(/date$/i, "time");

  return (
    <Panel title={dateLabel}>
      <div className="space-y-4">
        {successMessage ? <Alert message={successMessage} type="success" /> : null}
        {error ? <Alert message={error} type="error" /> : null}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label="Date"
            name="examDate"
            type="date"
            value={examDate}
            onChange={(event) => setExamDate(event.target.value)}
          />
          <Input
            label={timeLabel}
            name="examTime"
            type="time"
            value={examTime}
            onChange={(event) => setExamTime(event.target.value)}
          />
        </div>
        <p className={settingsMeta}>
          Adding your {dateLabel.toLowerCase()} helps us pace your practice and track your countdown.
        </p>
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="ghost" onClick={() => clear()} isLoading={clearing} disabled={saving}>
            I don&apos;t have a date yet
          </Button>
          <Button onClick={() => save()} isLoading={saving} disabled={clearing}>
            Save date
          </Button>
        </div>
      </div>
    </Panel>
  );
}
