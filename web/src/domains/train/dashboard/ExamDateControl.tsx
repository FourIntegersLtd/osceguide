"use client";

import { useEffect, useState } from "react";
import { HiOutlineCalendarDays } from "react-icons/hi2";
import {
  Alert,
  Modal,
  ModalContent,
  ModalHelper,
  ModalPrimaryButton,
  productTokens,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { updateMe } from "@/capabilities/account/api";
import { EXAM_PASSED, examTimeRemaining } from "@/domains/train/dashboard/examDate";

const { b2cFieldLabel, b2cInputBase } = productTokens;

/**
 * The dashboard's exam-date pill and its editor.
 *
 * The retiring `ScaDashboard` header carried a small calendar button that read
 * "Add exam date" until a date was set, then a live countdown ("5 days 3
 * hours"), then "Exam date passed" — and opened a modal to set or change it.
 * This is that control. It owns its own ticking state so the once-a-second
 * countdown re-renders the pill alone rather than the whole dashboard.
 *
 * `users.exam_date` is a plain date, so the editor is a single date field; the
 * legacy form's separate time input has nothing to write to now.
 */
export function ExamDateControl() {
  const { session, refresh } = useSession();
  const examDate = session?.user.exam_date ?? null;
  const [open, setOpen] = useState(false);

  /*
   * A tick that re-renders the pill once a second so the countdown stays live.
   * The remaining time is derived during the render rather than stored, so the
   * interval only bumps a counter from inside its callback — no synchronous
   * setState in the effect body, and no stale value when the date changes.
   */
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!examDate) return;
    const id = window.setInterval(() => setTick((tick) => tick + 1), 1000);
    return () => window.clearInterval(id);
  }, [examDate]);

  const remaining = examTimeRemaining(examDate);

  const label =
    !examDate || !remaining
      ? "Add exam date"
      : remaining === EXAM_PASSED
        ? "Exam date passed"
        : remaining;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title={examDate ? "Edit exam date" : "Add exam date"}
        className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-osce-meta font-medium text-b2c-text-secondary transition-colors hover:text-osce-accent"
      >
        <HiOutlineCalendarDays className="h-4 w-4 shrink-0" aria-hidden />
        <span className="truncate">{label}</span>
      </button>

      {open && (
        <Modal width="600px" height="fit-content" onClose={() => setOpen(false)}>
          <ExamDateForm
            initial={examDate}
            onSaved={() => {
              setOpen(false);
              void refresh();
            }}
          />
        </Modal>
      )}
    </>
  );
}

function ExamDateForm({ initial, onSaved }: { initial: string | null; onSaved: () => void }) {
  const [value, setValue] = useState(() => (initial ? initial.split("T")[0]! : ""));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    if (!value) {
      setError("Please select an exam date");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateMe({ exam_date: value });
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalContent className="space-y-4">
      <div>
        <h3 className="text-osce-subheading font-semibold text-osce-accent-hover">Exam date</h3>
        <ModalHelper className="mt-1">
          Adding your exam date helps us personalize your study plan and track your progress more
          effectively.
        </ModalHelper>
      </div>

      {error && <Alert tone="danger">{error}</Alert>}

      <div>
        <label htmlFor="dashboard-exam-date" className={b2cFieldLabel}>
          Exam date
        </label>
        <input
          id="dashboard-exam-date"
          type="date"
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setError(null);
          }}
          className={`${b2cInputBase} mt-1.5`}
        />
      </div>

      <div className="flex justify-end">
        <ModalPrimaryButton type="button" onClick={() => void save()} disabled={saving}>
          {saving ? "Saving…" : "Save date"}
        </ModalPrimaryButton>
      </div>
    </ModalContent>
  );
}
