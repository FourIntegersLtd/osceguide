"use client";

import React, { useCallback, useMemo, useRef, useState } from "react";
import { HiOutlineClock } from "react-icons/hi2";
import { addDays, format, isSameDay, startOfDay } from "date-fns";
import { useDismissOnOutside } from "@/foundation/hooks";
import { Button, B2CInlineError, productTokens, FoldSection } from "@/foundation/ui";
import {
  TIME_OPTIONS,
  TimeSlotList,
} from "@/capabilities/peer-practice/marketplace/formParts";
import { b2cInputBase, b2cCard } from "@/foundation/ui/productTokens";
import { MonthCalendar } from "@/capabilities/peer-practice/marketplace/MonthCalendar";
import { isScheduleInPast, toInstant } from "@/capabilities/peer-practice/support/time";

/** Wide enough for calendar left + time and note right on desktop. */
export const OFFER_SLOT_MODAL_WIDTH = "min(95vw, 800px)";

/** What the form asks for. The exam and the length are the caller's: the slot is for the exam being practised, thirty minutes long. */
export interface OfferSlotInput {
  startsAt: string;
  note: string | null;
}

/**
 * Offering a time you are free: a date, a time and an optional note.
 *
 * The retiring form, markup and copy. On a phone the time list is a dropdown
 * that closes on an outside press; from `md` up it is the full list beside the
 * calendar.
 */
export function OfferSlotForm({
  onSubmit,
  onCancel,
  isLoading = false,
  availabilityLabel = "I am available to practise on",
}: {
  onSubmit: (input: OfferSlotInput) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  availabilityLabel?: string;
}) {
  const [day, setDay] = useState("");
  const [pickedTime, setTime] = useState("");
  const [note, setNote] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [timeOpen, setTimeOpen] = useState(false);
  const timeRef = useRef<HTMLDivElement>(null);

  const today = useMemo(() => startOfDay(new Date()), []);
  const maxDate = useMemo(() => startOfDay(addDays(new Date(), 14)), []);

  const visibleTimeOptions = useMemo(
    () => (day ? TIME_OPTIONS.filter((option) => !isScheduleInPast(day, option.value)) : TIME_OPTIONS),
    [day],
  );

  // A time that has slipped into the past since it was picked stops being
  // selected, derived rather than corrected in an effect.
  const time = pickedTime && day && isScheduleInPast(day, pickedTime) ? "" : pickedTime;
  const hasDate = Boolean(day);
  const hasTime = Boolean(time);

  const selectedDate = day ? new Date(`${day}T12:00:00`) : null;
  const selectedAnotherDay = selectedDate !== null && !isSameDay(selectedDate, today);

  const closeTime = useCallback(() => setTimeOpen(false), []);
  useDismissOnOutside(timeRef, timeOpen, closeTime);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setValidationError(null);
    if (!day || !time) {
      setValidationError("Choose a date and a time first.");
      return;
    }
    if (isScheduleInPast(day, time)) {
      setValidationError("Choose a date and time in the future.");
      return;
    }
    await onSubmit({ startsAt: toInstant(day, time), note: note.trim() || null });
    setDay("");
    setTime("");
    setNote("");
  };

  const timeLabel = TIME_OPTIONS.find((option) => option.value === time)?.label;
  const requestSummary =
    day && time ? `Request for: ${format(new Date(`${day}T12:00:00`), "d MMM")}, ${timeLabel ?? time}` : null;

  return (
    <form onSubmit={submit} className="availability-form space-y-6 text-osce-body">
      <div>
        <h2 className="text-osce-title font-semibold text-osce-ink-900">{availabilityLabel}</h2>
        <p className="mt-1.5 text-osce-body text-b2c-text-muted">
          Choose when you are free. Someone can claim the slot and you will both get a video practice session.
        </p>
      </div>

      <div className="grid grid-cols-1 items-start gap-6 md:grid-cols-[minmax(0,1fr)_minmax(16rem,18.5rem)]">
        <FoldSection number={1} title="Choose a date">
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
        </FoldSection>

        <div className="flex min-w-0 flex-col gap-6">
          <FoldSection number={2} title="Choose a time" description={hasDate ? undefined : "Choose a date first"}>
            <div ref={timeRef} className="relative md:hidden">
              <button
                type="button"
                disabled={!hasDate}
                aria-disabled={!hasDate}
                aria-label="Choose a time"
                onClick={() => hasDate && setTimeOpen((open) => !open)}
                className={`flex w-full items-center gap-3 rounded-lg border px-4 py-3.5 text-left text-osce-body outline-none transition-colors ${
                  hasDate
                    ? "border-b2c-border bg-osce-surface hover:border-b2c-text-muted focus:border-osce-accent focus:ring-2 focus:ring-osce-accent"
                    : "cursor-not-allowed border-b2c-border/80 bg-b2c-surface-muted opacity-70"
                }`}
              >
                <HiOutlineClock className="h-4 w-4 shrink-0 text-b2c-text-muted" />
                <span className={hasTime ? "text-osce-ink-900" : "text-b2c-text-muted"}>
                  {hasTime ? (timeLabel ?? "Select a time") : "Select a time"}
                </span>
                <svg
                  className={`ml-auto h-4 w-4 shrink-0 text-b2c-text-muted transition-transform ${timeOpen ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {timeOpen && hasDate ? (
                <div className={`absolute z-10 mt-2 max-h-56 w-full overflow-auto ${b2cCard}`} role="listbox" aria-label="Choose a time">
                  <TimeSlotList
                    options={visibleTimeOptions}
                    selected={time}
                    onSelect={(value) => {
                      setTime(value);
                      setTimeOpen(false);
                    }}
                  />
                </div>
              ) : null}
            </div>

            <div
              className={`hidden min-h-64 max-h-80 overflow-auto md:block ${
                hasDate ? b2cCard : "rounded-osce-lg border border-b2c-border bg-b2c-surface-muted"
              }`}
              role="listbox"
              aria-label="Choose a time"
              aria-disabled={!hasDate}
            >
              {hasDate ? (
                <TimeSlotList options={visibleTimeOptions} selected={time} onSelect={setTime} />
              ) : (
                <p className="flex min-h-64 items-center justify-center gap-2 px-4 py-8 text-center text-osce-body text-b2c-text-muted">
                  <HiOutlineClock className="h-4 w-4 shrink-0" aria-hidden />
                  Choose a date first
                </p>
              )}
            </div>
          </FoldSection>
        </div>
      </div>

      <FoldSection
        number={3}
        title="Add a note"
        meta={<span className="text-osce-meta font-normal text-ink-subtle">Optional</span>}
      >
        <input
          type="text"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="e.g. Looking for someone preparing for April"
          maxLength={100}
          className={`${b2cInputBase} w-full`}
        />
      </FoldSection>

      <B2CInlineError message={validationError} />

      <div className="space-y-3 border-t border-b2c-border pt-5">
        {requestSummary ? (
          <p className={productTokens.b2cMonoEyebrow}>{requestSummary}</p>
        ) : (
          <p className="text-osce-meta leading-relaxed text-b2c-text-muted">
            Pick a date and a time to continue.
          </p>
        )}

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="secondary" size="md" onClick={onCancel} disabled={isLoading} className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading} disabled={!hasDate || !hasTime} className="w-full sm:w-auto">
            Select & continue
          </Button>
        </div>
      </div>
    </form>
  );
}
