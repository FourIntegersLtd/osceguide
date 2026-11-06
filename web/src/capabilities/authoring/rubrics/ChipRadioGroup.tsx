"use client";

import type { KeyboardEvent, ReactNode } from "react";
import { cn } from "@/foundation/ui";
import { radioFocusTarget } from "@/capabilities/authoring/rubrics/chipRadioKeys";
import { boardChip } from "@/foundation/ui/boardKit";

/** A row of chips of which exactly one is chosen: radios to a screen reader, arrow keys move focus and Space or Enter chooses. */
export function ChipRadioGroup<Id extends string>({
  label,
  options,
  value,
  onChange,
  disabled,
  leading,
}: {
  label: string;
  options: readonly { id: Id; label: string }[];
  /** The chosen id; null when none matches. */
  value: Id | null;
  onChange: (id: Id) => void;
  disabled?: boolean;
  leading?: ReactNode;
}) {
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, at: number) => {
    const to = radioFocusTarget(options.length, at, event.key);
    if (to === null) return;
    event.preventDefault();
    event.currentTarget.parentElement?.querySelectorAll<HTMLElement>('[role="radio"]')[to]?.focus();
  };
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap items-center gap-2">
      {leading}
      {options.map((option, n) => {
        const on = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={on}
            tabIndex={on || (value === null && n === 0) ? 0 : -1}
            disabled={disabled}
            onClick={() => onChange(option.id)}
            onKeyDown={(event) => onKeyDown(event, n)}
            className={cn(boardChip(on ? "info" : "neutral"), "h-9 cursor-pointer px-3.5")}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
