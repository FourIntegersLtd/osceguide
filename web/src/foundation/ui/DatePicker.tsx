"use client";

import type { CSSProperties } from "react";
import { DayPicker } from "react-day-picker";
import "react-day-picker/style.css";
import { dayFromIso, isoFromDay } from "@/foundation/ui/dateDay";

const tokenStyle = {
  "--rdp-accent-color": "rgb(var(--color-accent))",
  "--rdp-accent-background-color": "rgb(var(--color-accent-subtle))",
  "--rdp-day-height": "40px",
  "--rdp-day-width": "40px",
  "--rdp-day_button-height": "38px",
  "--rdp-day_button-width": "38px",
  color: "rgb(var(--color-ink))",
} as CSSProperties;

/**
 * The one calendar: pick a single day. `value` and `onChange` are `YYYY-MM-DD`
 * strings (what the API stores). Painted with the semantic tokens, so it
 * follows the arm's skin and needs no per-screen styling.
 */
export function DatePicker({
  value,
  onChange,
  disabled,
}: {
  value: string | null;
  onChange: (day: string) => void;
  disabled?: boolean;
}) {
  const selected = dayFromIso(value);
  return (
    <DayPicker
      mode="single"
      selected={selected}
      defaultMonth={selected}
      onSelect={(day) => {
        if (day) onChange(isoFromDay(day));
      }}
      disabled={disabled}
      weekStartsOn={1}
      style={tokenStyle}
    />
  );
}
