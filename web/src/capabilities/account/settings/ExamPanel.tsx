"use client";

import { useState } from "react";
import { AsyncBoundary, Input, Panel } from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { AddExamDate } from "@/capabilities/account/AddExamDate";
import { readMe, type Me } from "@/capabilities/account/api";
import { examLabel, NO_EXAM_LABEL } from "@/capabilities/account/settings/examLabel";
import { settingsMeta } from "@/capabilities/account/settings/SettingsKit";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

/**
 * Which exam this account is for, and when they sit it.
 *
 * The retiring client's Exam tab: an "Exam" card with the type read-only, and
 * an "Exam date" card that is yours to set: a calendar, day only.
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
        dateLabel={settings.date_label}
      />
    </>
  );
}

/** The date card: click a day to save it, or clear it (the countdown and pacing stop). Day only, no time. */
function ExamDateCard({ initialDate, dateLabel }: { initialDate: string; dateLabel: string }) {
  const [examDate, setExamDate] = useState(initialDate);
  const [successMessage, setSuccessMessage] = useState("");

  return (
    <Panel title={dateLabel}>
      <div className="space-y-4">
        {successMessage ? <Alert message={successMessage} type="success" /> : null}
        <AddExamDate
          examDate={examDate || null}
          allowClear
          onSaved={(day) => {
            setExamDate(day ?? "");
            setSuccessMessage(day ? `${dateLabel} updated` : `${dateLabel} cleared`);
          }}
        />
        <p className={settingsMeta}>
          Adding your {dateLabel.toLowerCase()} helps us pace your practice and track your countdown.
        </p>
      </div>
    </Panel>
  );
}
