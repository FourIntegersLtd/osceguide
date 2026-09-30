"use client";

import { useMemo, useState } from "react";
import { HiOutlineChevronLeft, HiOutlineChevronRight } from "react-icons/hi2";
import {
  addDays,
  addMonths,
  format,
  isAfter,
  isBefore,
  isSameDay,
  isSameMonth,
  startOfDay,
  startOfMonth,
  startOfWeek,
} from "date-fns";

/**
 * The month grid the availability form is picked from.
 *
 * Written here rather than pulled in: `globals.css` already carries the whole
 * appearance of this calendar — the selected disc, today's ring, today's dot
 * once another day is chosen, the blurred disabled days — keyed on
 * `react-day-picker`'s class names, and that stylesheet came across with the
 * port. Emitting the same class names renders the identical calendar with no
 * new dependency, and the Tailwind classes below stand in for the library's own
 * base sheet, which did not.
 */
export function MonthCalendar({
  selected,
  onSelect,
  fromDate,
  toDate,
}: {
  selected: Date | null;
  onSelect: (day: Date) => void;
  fromDate: Date;
  toDate: Date;
}) {
  const [month, setMonth] = useState(() => startOfMonth(selected ?? fromDate));
  const today = useMemo(() => startOfDay(new Date()), []);

  const weeks = useMemo(() => {
    const first = startOfWeek(startOfMonth(month), { weekStartsOn: 1 });
    return Array.from({ length: 6 }, (_, week) =>
      Array.from({ length: 7 }, (_, day) => addDays(first, week * 7 + day)),
    );
  }, [month]);

  // The header row is the first week's seven days, named. Built from the same
  // arithmetic so the column order cannot drift from the cells beneath it.
  const weekdays = useMemo(() => {
    const first = startOfWeek(startOfMonth(month), { weekStartsOn: 1 });
    return Array.from({ length: 7 }, (_, day) => addDays(first, day));
  }, [month]);

  const canGoBack = isAfter(startOfMonth(month), startOfMonth(fromDate));
  const canGoForward = isBefore(startOfMonth(month), startOfMonth(toDate));

  return (
    <div className="rdp-root w-full border-0">
      <div className="rdp-months w-full">
        <div className="rdp-month w-full">
          <div className="rdp-month_caption mb-2 flex items-center justify-between px-1">
            <button
              type="button"
              aria-label="Previous month"
              disabled={!canGoBack}
              onClick={() => setMonth((m) => addMonths(m, -1))}
              className="flex h-8 w-8 items-center justify-center rounded-md text-b2c-text-secondary transition-colors hover:bg-b2c-surface-muted disabled:pointer-events-none disabled:opacity-30"
            >
              <HiOutlineChevronLeft className="h-4 w-4" aria-hidden />
            </button>
            <span
              aria-live="polite"
              className="text-osce-body font-semibold text-osce-ink-900"
            >
              {format(month, "MMMM yyyy")}
            </span>
            <button
              type="button"
              aria-label="Next month"
              disabled={!canGoForward}
              onClick={() => setMonth((m) => addMonths(m, 1))}
              className="flex h-8 w-8 items-center justify-center rounded-md text-b2c-text-secondary transition-colors hover:bg-b2c-surface-muted disabled:pointer-events-none disabled:opacity-30"
            >
              <HiOutlineChevronRight className="h-4 w-4" aria-hidden />
            </button>
          </div>

          <table className="rdp-month_grid w-full table-fixed border-collapse">
            <thead className="rdp-weekdays">
              <tr>
                {weekdays.map((day) => (
                  <th
                    key={day.toISOString()}
                    scope="col"
                    abbr={format(day, "EEEE")}
                    className="rdp-weekday pb-1 text-osce-caption font-medium text-b2c-text-muted"
                  >
                    {format(day, "EEE").toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="rdp-weeks">
              {weeks.map((week) => (
                <tr key={week.map((day) => day.getTime()).join()} className="rdp-week">
                  {week.map((day) => (
                    <DayCell
                      key={day.toISOString()}
                      day={day}
                      month={month}
                      today={today}
                      selected={selected}
                      fromDate={fromDate}
                      toDate={toDate}
                      onSelect={onSelect}
                    />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function DayCell({
  day,
  month,
  today,
  selected,
  fromDate,
  toDate,
  onSelect,
}: {
  day: Date;
  month: Date;
  today: Date;
  selected: Date | null;
  fromDate: Date;
  toDate: Date;
  onSelect: (day: Date) => void;
}) {
  const outside = !isSameMonth(day, month);
  const disabled = isBefore(day, fromDate) || isAfter(day, toDate);
  const isSelected = selected !== null && isSameDay(day, selected);
  const isToday = isSameDay(day, today);

  const classes = [
    "rdp-day",
    "p-0.5 text-center",
    outside && "rdp-outside",
    disabled && "rdp-disabled rdp-day_disabled",
    isSelected && "rdp-selected",
    isToday && "rdp-today rdp-day_today",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <td className={classes}>
      <button
        type="button"
        disabled={disabled}
        aria-pressed={isSelected}
        aria-label={format(day, "EEEE d MMMM yyyy")}
        onClick={() => onSelect(day)}
        className={`rdp-day_button mx-auto flex h-9 w-9 items-center justify-center rounded-full border border-transparent text-osce-body transition-colors hover:bg-b2c-surface-muted focus:outline-none focus:ring-2 focus:ring-osce-accent ${
          outside ? "text-b2c-text-muted" : "text-osce-ink-900"
        }`}
      >
        {format(day, "d")}
      </button>
    </td>
  );
}
