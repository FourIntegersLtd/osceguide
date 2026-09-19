"use client";

import { useState } from "react";
import { HiOutlineAcademicCap } from "react-icons/hi2";
import { Alert, AsyncBoundary, Button, cn, productTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { readMe, updateMe } from "@/capabilities/account/api";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cInputBase } = productTokens;

/**
 * Which exam this account is for, and when they sit it.
 *
 * The retiring client's Exam tab, with the same two fields and the same shape:
 * the exam is read-only with a line telling you who to ask, and the date is
 * yours to set. It was left out of the port because nothing stored either —
 * `users.exam_code` and `users.exam_date` both exist now.
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
      <AsyncBoundary state={state}>{(me) => <ExamForm key={me.id} me={me} />}</AsyncBoundary>
    </SettingsTabShell>
  );
}

function ExamForm({ me }: { me: Awaited<ReturnType<typeof readMe>> }) {
  const { codes } = useCurrentExam();
  const [examDate, setExamDate] = useState(me.exam_date ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      // Empty clears it: the backend distinguishes "not mentioned" from "set
      // to nothing", which is what makes removing a date possible at all.
      await updateMe({ exam_date: examDate || null });
      setSaved(true);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  // What they signed up to sit, or — if they have since bought others — what
  // they hold. One line either way; this is not a place to switch.
  const examLabel = (me.exam_code ?? codes[0] ?? "").toUpperCase();

  return (
    <div className="space-y-4">
      {error && <Alert tone="danger">{error}</Alert>}
      {saved && <Alert tone="success">Saved.</Alert>}

      <div>
        <label htmlFor="settings-exam-type" className={b2cFieldLabel}>
          Exam type
        </label>
        <div className="relative mt-1.5">
          <HiOutlineAcademicCap
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-b2c-text-muted"
            aria-hidden
          />
          <input
            id="settings-exam-type"
            type="text"
            value={examLabel || "Not set"}
            disabled
            className={cn(b2cInputBase, "pl-9")}
          />
        </div>
        <p className="mt-1.5 text-osce-meta text-b2c-text-muted">
          Exam type is set when you signed up. Contact support if you need to switch exams.
        </p>
      </div>

      <div>
        <label htmlFor="settings-exam-date" className={b2cFieldLabel}>
          Exam date
        </label>
        <input
          id="settings-exam-date"
          type="date"
          value={examDate}
          onChange={(event) => {
            setExamDate(event.target.value);
            setSaved(false);
          }}
          className={cn(b2cInputBase, "mt-1.5")}
        />
        <p className="mt-1.5 text-osce-meta text-b2c-text-muted">
          Your dashboard counts down to it, and it appears beside your exam in the menu.
        </p>
      </div>

      <Button type="button" variant="primary" size="md" onClick={() => void save()} disabled={saving}>
        {saving ? "Saving..." : "Save"}
      </Button>
    </div>
  );
}
