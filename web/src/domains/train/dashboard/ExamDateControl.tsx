"use client";

import { useEffect, useRef, useState } from "react";
import { HiOutlineCalendarDays, HiOutlinePencil } from "react-icons/hi2";
import { Button, productTokens } from "@/foundation/ui";
import { useCurrentExam, useSession } from "@/foundation/session";
import { AddExamDate } from "@/capabilities/account/AddExamDate";
import { examCountdown } from "@/domains/train/dashboard/examDate";
import { dayFromIso } from "@/foundation/ui/dateDay";

const SAVED_FLASH_MS = 700;

/**
 * The dashboard header's right side (canvas `train-dashboard`): the exam date
 * with a pencil that opens the calendar, the countdown underneath, or an
 * "Add exam date" button while none is set. Picking a day saves it, says
 * "Saved" for a moment and closes the popover; "Clear date" removes it.
 */
export function ExamDateControl() {
  const { session, refresh } = useSession();
  const { settings } = useCurrentExam();
  const examDate = session?.user.exam_date ?? null;
  const [open, setOpen] = useState(false);
  const [saved, setSaved] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const onSaved = () => {
    void refresh();
    setSaved(true);
    timer.current = window.setTimeout(() => {
      setSaved(false);
      setOpen(false);
    }, SAVED_FLASH_MS);
  };
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const day = dayFromIso(examDate);
  const dateText = day?.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  const countdown = examCountdown(examDate);

  return (
    <div ref={root} className="relative flex flex-col items-start gap-0.5 sm:items-end">
      {dateText ? (
        <div className="flex items-center gap-1">
          <span className="text-osce-body font-medium text-osce-ink-900">
            {settings.date_label.replace(/ date$/i, "")}: {dateText}
          </span>
          <button
            type="button"
            className={productTokens.b2cIconButton}
            aria-label={`Edit ${settings.date_label.toLowerCase()}`}
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            <HiOutlinePencil className="h-4 w-4" aria-hidden />
          </button>
        </div>
      ) : (
        <Button type="button" variant="secondary" size="md" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          <HiOutlineCalendarDays className="h-4 w-4 shrink-0" aria-hidden />
          Add {settings.date_label.toLowerCase()}
        </Button>
      )}
      {countdown ? <span className="text-osce-meta text-b2c-text-muted">{countdown}</span> : null}

      {open ? (
        <div
          role="dialog"
          aria-label={settings.date_label}
          className="absolute right-0 top-full z-30 mt-2 rounded-osce-lg border border-b2c-border bg-osce-surface p-3 shadow-[0_12px_32px_rgba(16,24,40,0.12)]"
        >
          {saved ? (
            <p role="status" className="px-6 py-10 text-center font-medium text-osce-ink-900">
              Saved
            </p>
          ) : (
            <AddExamDate examDate={examDate} onSaved={onSaved} allowClear />
          )}
        </div>
      ) : null}
    </div>
  );
}
