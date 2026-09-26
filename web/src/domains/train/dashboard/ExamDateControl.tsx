"use client";

import { useEffect, useState } from "react";
import { HiOutlineCalendarDays } from "react-icons/hi2";
import { Modal } from "@/foundation/ui";
import { useCurrentExam, useSession } from "@/foundation/session";
import { AddExamDate } from "@/domains/train/dashboard/AddExamDate";
import { EXAM_PASSED, examMoment, examTimeRemaining } from "@/domains/train/dashboard/examDate";

/**
 * The dashboard's exam-date pill and its editor.
 *
 * The retiring `ScaDashboard` header carried a small calendar button that read
 * "Add exam date" until a date was set, then a live countdown ("5 days 3
 * hours"), then "Exam date passed" — and opened a modal to set or change it.
 * This is that control. It owns its own ticking state so the once-a-second
 * countdown re-renders the pill alone rather than the whole dashboard.
 *
 * The modal holds the old `AddExamDate` card, date and time, and stays open
 * after a save as the old one did, with the countdown behind it refreshed.
 */
export function ExamDateControl() {
  const { session, refresh } = useSession();
  const { code: examCode } = useCurrentExam();
  const examDate = examMoment(session?.user.exam_date, session?.user.exam_time);
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
          <AddExamDate
            examDate={session?.user.exam_date ?? null}
            examTime={session?.user.exam_time ?? null}
            isOrtho={examCode === "ortho"}
            onSaved={() => void refresh()}
          />
        </Modal>
      )}
    </>
  );
}
