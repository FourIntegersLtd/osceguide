"use client";

import React, { useMemo, useState } from "react";
import { HiOutlineCalendarDays, HiOutlineCheckCircle } from "react-icons/hi2";
import { addDays, format, isSameDay, startOfDay } from "date-fns";
import { Button, B2CInlineError, ModalLead } from "@/foundation/ui";
import {
  FormStep,
  TIME_OPTIONS,
  TimeSlotList,
} from "@/capabilities/peer-practice/marketplace/formParts";
import { b2cInputBase, b2cInset } from "@/foundation/ui/productTokens";
import { MonthCalendar } from "@/capabilities/peer-practice/marketplace/MonthCalendar";
import { isScheduleInPast, toInstant } from "@/capabilities/peer-practice/support/time";

/** Wide enough for calendar left + time and note right on desktop. */
export const OFFER_SLOT_MODAL_WIDTH = "min(95vw, 800px)";

export interface ExamOption {
  code: string;
  name: string;
}

export interface OfferSlotInput {
  examCode: string;
  startsAt: string;
  durationMinutes: number;
  note: string | null;
}

const DURATIONS = [15, 20, 30, 45, 60];

/**
 * Offering a time you are free.
 *
 * The exam and the length are chosen here, which the retiring form did not
 * have to do: the old app was one exam per deployment and a fixed thirty
 * minutes. `platform-api` addresses a slot to an exam, so the capability asks
 * rather than assuming one — the same reason it takes its audience from the
 * caller instead of knowing about consumers.
 */
export function OfferSlotForm({
  exams,
  onSubmit,
  onCancel,
  isLoading = false,
  availabilityLabel = "I am available to practice on",
}: {
  exams: ExamOption[];
  onSubmit: (input: OfferSlotInput) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  availabilityLabel?: string;
}) {
  const [examCode, setExamCode] = useState(exams[0]?.code ?? "");
  const [duration, setDuration] = useState(30);
  const [day, setDay] = useState("");
  const [pickedTime, setTime] = useState("");
  const [note, setNote] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const today = useMemo(() => startOfDay(new Date()), []);
  const maxDate = useMemo(() => startOfDay(addDays(new Date(), 14)), []);

  const visibleTimeOptions = useMemo(
    () => (day ? TIME_OPTIONS.filter((option) => !isScheduleInPast(day, option.value)) : TIME_OPTIONS),
    [day],
  );

  // A time that has slipped into the past since it was picked stops being
  // selected, derived rather than corrected in an effect: the old form set
  // state from an effect and re-rendered twice for every click on the grid.
  const time = pickedTime && day && isScheduleInPast(day, pickedTime) ? "" : pickedTime;

  const selectedDate = day ? new Date(`${day}T12:00:00`) : null;
  const selectedAnotherDay = selectedDate !== null && !isSameDay(selectedDate, today);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setValidationError(null);
    if (!examCode) {
      setValidationError("Choose an exam first.");
      return;
    }
    if (!day || !time) {
      setValidationError("Choose a date and a time first.");
      return;
    }
    if (isScheduleInPast(day, time)) {
      setValidationError("Choose a date and time in the future.");
      return;
    }
    await onSubmit({
      examCode,
      startsAt: toInstant(day, time),
      durationMinutes: duration,
      note: note.trim() || null,
    });
    setDay("");
    setTime("");
    setNote("");
  };

  const requestSummary =
    day && time
      ? `Request for: ${format(new Date(`${day}T12:00:00`), "d MMM")}, ${
          TIME_OPTIONS.find((option) => option.value === time)?.label ?? time
        }`
      : null;

  return (
    <form onSubmit={submit} className="availability-form space-y-6 text-osce-body">
      <ModalLead
        title={availabilityLabel}
        description="Choose when you are free. Someone can claim the slot, and you will both get a video practice session."
        icon={<HiOutlineCalendarDays className="h-5 w-5" />}
      />

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5">
          <span className="text-osce-meta font-medium text-osce-ink-900">Exam</span>
          <select
            value={examCode}
            onChange={(event) => setExamCode(event.target.value)}
            className={b2cInputBase}
          >
            {exams.map((exam) => (
              <option key={exam.code} value={exam.code}>
                {exam.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-osce-meta font-medium text-osce-ink-900">Length</span>
          <select
            value={duration}
            onChange={(event) => setDuration(Number(event.target.value))}
            className={b2cInputBase}
          >
            {DURATIONS.map((minutes) => (
              <option key={minutes} value={minutes}>
                {minutes} minutes
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_minmax(16rem,18.5rem)]">
        <FormStep step={1} label="Choose a date" done={Boolean(day)}>
          <div
            className={`availability-form-calendar w-full overflow-hidden rounded-xl bg-b2c-surface-muted p-3 sm:p-4 ${
              selectedAnotherDay ? "availability-form-calendar--other-day-selected" : ""
            }`}
          >
            <MonthCalendar
              selected={selectedDate}
              onSelect={(picked) => setDay(format(picked, "yyyy-MM-dd"))}
              fromDate={today}
              toDate={maxDate}
            />
          </div>
        </FormStep>

        <FormStep
          step={2}
          label="Choose a time"
          done={Boolean(time)}
          hint={day ? undefined : "Choose a date first"}
        >
          <div
            className={`max-h-80 min-h-64 overflow-auto ${
              day ? b2cInset : "rounded-osce-lg border border-b2c-border bg-b2c-surface-muted"
            }`}
            role="listbox"
            aria-label="Choose a time"
            aria-disabled={!day}
          >
            {day ? (
              <TimeSlotList options={visibleTimeOptions} selected={time} onSelect={setTime} />
            ) : (
              <p className="flex min-h-64 items-center justify-center px-4 py-8 text-center text-osce-body text-b2c-text-muted">
                Choose a date first
              </p>
            )}
          </div>
        </FormStep>
      </div>

      <FormStep step={3} label="Add a note" optional done={Boolean(note)}>
        <input
          type="text"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="e.g. Looking for someone preparing for April"
          maxLength={100}
          className={`${b2cInputBase} w-full`}
        />
      </FormStep>

      <B2CInlineError message={validationError} />

      <div className="space-y-3 border-t border-b2c-border pt-5">
        {requestSummary ? (
          <div className="flex items-start gap-2.5 rounded-xl bg-osce-accent-muted/40 px-4 py-3">
            <HiOutlineCheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
            <p className="min-w-0 text-osce-meta leading-relaxed text-b2c-text-secondary">
              {requestSummary}
            </p>
          </div>
        ) : (
          <p className="text-osce-meta leading-relaxed text-b2c-text-muted">
            Pick a date and a time to continue.
          </p>
        )}

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="secondary" size="md" onClick={onCancel} disabled={isLoading} className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button type="submit" variant="commit" size="md" disabled={isLoading || !day || !time} className="w-full sm:w-auto">
            {isLoading ? "Posting..." : "Select & continue"}
          </Button>
        </div>
      </div>
    </form>
  );
}
