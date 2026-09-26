"use client";

import { useState } from "react";
import { HiOutlineCalendarDays } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalHelper,
  ModalPrimaryButton,
  productTokens,
} from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { readMe, updateMe, type Me } from "@/capabilities/account/api";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const {
  b2cFieldLabel,
  b2cSettingsCardHeaderIcon,
  b2cSettingsFieldInput,
  b2cSettingsFieldInputDisabled,
} = productTokens;

/** The retiring client's names for each exam; anything else is its code in capitals. */
const EXAM_LABELS: Record<string, string> = {
  sca: "SCA",
  plab: "PLAB",
  ortho: "Orthopaedic interview",
};

/** How an exam code reads on the settings screen. Empty when there is none. */
export function examLabel(code: string | null | undefined): string {
  if (!code) return "";
  return EXAM_LABELS[code] ?? code.toUpperCase();
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
  const { codes } = useCurrentExam();
  // What they signed up to sit, or — if they have since bought others — what
  // they hold. The old screen fell back to "sca" when nothing was set.
  const code = me.exam_code ?? codes[0] ?? "sca";
  const isOrtho = code === "ortho";

  return (
    <>
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          <HiOutlineCalendarDays className={b2cSettingsCardHeaderIcon} aria-hidden />
          Exam
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-4">
          <ModalHelper className="mt-0">
            Your exam type and date — the same options available from your dashboard.
          </ModalHelper>
          <div>
            <label htmlFor="settings-exam-type" className={b2cFieldLabel}>
              Exam type
            </label>
            <input
              id="settings-exam-type"
              type="text"
              value={examLabel(code)}
              disabled
              className={b2cSettingsFieldInputDisabled}
            />
            <p className="mt-1.5 text-osce-meta text-b2c-text-muted">
              Exam type is set when you signed up. Contact support if you need to switch exams.
            </p>
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>

      <ExamDateCard
        initialDate={me.exam_date ?? ""}
        initialTime={(me.exam_time ?? "").slice(0, 5)}
        isOrtho={isOrtho}
      />
    </>
  );
}

/** The old `AddExamDate` card: date required, time optional, toasts on save. */
function ExamDateCard({
  initialDate,
  initialTime,
  isOrtho,
}: {
  initialDate: string;
  initialTime: string;
  isOrtho: boolean;
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

  const noun = isOrtho ? "interview" : "exam";

  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader className="text-osce-accent-hover">
        {isOrtho ? "Interview date" : "Exam date"}
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        <ModalHelper className="mt-0">
          Adding your {noun} date helps us personalize your study plan and track your progress more
          effectively.
        </ModalHelper>
        {successMessage ? <Alert message={successMessage} type="success" /> : null}
        {error ? <Alert message={error} type="error" /> : null}
        <div className="flex flex-col gap-2.5 sm:flex-row">
          <label htmlFor="settings-exam-date" className="sr-only">
            {isOrtho ? "Interview date" : "Exam date"}
          </label>
          <input
            id="settings-exam-date"
            type="date"
            value={examDate}
            onChange={(event) => setExamDate(event.target.value)}
            className={`${b2cSettingsFieldInput} flex-1`}
          />
          <label htmlFor="settings-exam-time" className="sr-only">
            {isOrtho ? "Interview time" : "Exam time"}
          </label>
          <input
            id="settings-exam-time"
            type="time"
            value={examTime}
            onChange={(event) => setExamTime(event.target.value)}
            className={`${b2cSettingsFieldInput} sm:w-32`}
          />
        </div>
      </B2CPanelCardBody>
      <B2CPanelCardFooter>
        <ModalPrimaryButton type="button" onClick={() => void save()} disabled={saving}>
          {saving ? "Saving…" : "Save date"}
        </ModalPrimaryButton>
      </B2CPanelCardFooter>
    </B2CPanelCard>
  );
}
