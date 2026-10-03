"use client";

import { useState } from "react";
import { HiOutlineCalendarDays } from "react-icons/hi2";
import { Button, Modal } from "@/foundation/ui";
import { useCurrentExam, useSession } from "@/foundation/session";
import { AddExamDate } from "@/domains/train/dashboard/AddExamDate";
import { examMoment } from "@/domains/train/dashboard/examDate";

/**
 * The dashboard header's one secondary action (canvas `train-dashboard`):
 * "Add exam date" until a date is set, then "Edit exam date". The countdown
 * itself is the header's subtitle. The modal holds the old `AddExamDate`
 * card and stays open after a save, with the countdown behind it refreshed.
 */
export function ExamDateControl() {
  const { session, refresh } = useSession();
  const { settings } = useCurrentExam();
  const examDate = examMoment(session?.user.exam_date, session?.user.exam_time);
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button type="button" variant="secondary" size="md" onClick={() => setOpen(true)}>
        <HiOutlineCalendarDays className="h-4 w-4 shrink-0" aria-hidden />
        {examDate ? "Edit exam date" : "Add exam date"}
      </Button>

      {open && (
        <Modal width="600px" height="fit-content" onClose={() => setOpen(false)}>
          <AddExamDate
            examDate={session?.user.exam_date ?? null}
            examTime={session?.user.exam_time ?? null}
            dateLabel={settings.date_label}
            onSaved={() => void refresh()}
          />
        </Modal>
      )}
    </>
  );
}
