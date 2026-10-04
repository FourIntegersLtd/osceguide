"use client";

import { Input, cn } from "@/foundation/ui";
import type { Programme, SittingMode } from "@/domains/assess/api";

/**
 * The two fields every sitting form has.
 *
 * Scheduling one and correcting one are the same questions — which mode, which
 * programme — so they are one pair of components rather than two screens that
 * have to be read together to notice they agree. The edit screen also needs to
 * freeze them mid-form once a circuit has started, which is what `disabled` is
 * for: a field that will be refused is shown as closed, not offered and argued
 * with.
 */

/** One programme, narrowed to what a sitting form prints and picks with. */
export type ProgrammeChoice = Pick<Programme, "id" | "exam_name" | "exam_code" | "status">;

export function ModeField({
  value,
  onChange,
  disabled = false,
  hint,
}: {
  value: SittingMode;
  onChange: (mode: SittingMode) => void;
  disabled?: boolean;
  hint?: string;
}) {
  return (
    <fieldset className="flex flex-col gap-1.5" disabled={disabled}>
      <legend className="text-sm font-medium text-ink">Mode</legend>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {(
          [
            ["exam", "Exam", "Marked, signed off and released"],
            ["training", "Training", "Feedback straight to the trainee"],
          ] as const
        ).map(([option, label, blurb]) => (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            aria-pressed={value === option}
            className={cn(
              "flex flex-col items-start gap-0.5 rounded-control border px-4 py-3 text-left transition-colors disabled:opacity-60",
              value === option
                ? "border-b2b-headline bg-canvas"
                : "border-b2b-border bg-b2b-surface hover:bg-canvas",
            )}
          >
            <span className="text-osce-body font-medium text-b2b-headline">{label}</span>
            <span className="text-osce-meta text-b2b-mid">{blurb}</span>
          </button>
        ))}
      </div>
      <p className="text-sm text-ink-muted">
        {hint ??
          (value === "exam"
            ? "One candidate takes every station, up to twelve. You cannot add trainees once it has started."
            : "Each trainee is paired with one station, and they rotate.")}
      </p>
    </fieldset>
  );
}

/**
 * The programme, which is where the marking template comes from.
 *
 * The retiring screen called this "Feedback template" and listed published
 * template versions; this backend resolves the rubric through the programme, so
 * the pick is the programme and the sentence under it says so rather than
 * leaving a reviewer looking for a template picker that no longer exists.
 */
export function ProgrammeField({
  value,
  onChange,
  programmes,
  disabled = false,
}: {
  value: string;
  onChange: (programmeId: string) => void;
  programmes: ProgrammeChoice[];
  disabled?: boolean;
}) {
  const selected = programmes.find((programme) => programme.id === value);
  return (
    <div className="flex flex-col gap-1.5">
      <FieldSelect
        label="Programme"
        value={value}
        onChange={onChange}
        disabled={disabled}
        options={programmes.map((programme) => ({
          value: programme.id,
          label: `${programme.exam_name} (${programme.exam_code})`,
        }))}
      />
      {selected ? (
        <p className="text-sm text-ink-muted">
          Marking and feedback follow the published marking scheme for {selected.exam_name}, so there is nothing else to choose.
        </p>
      ) : null}
    </div>
  );
}

/** The examination's date. Editable for the life of the record — a moved date misleads nobody about a mark already given. */
export function ScheduledForField({
  value,
  onChange,
  hint = "Leave empty to schedule it later.",
}: {
  value: string;
  onChange: (value: string) => void;
  hint?: string;
}) {
  return (
    <Input
      label="Scheduled for"
      type="datetime-local"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      hint={hint}
    />
  );
}

/** A labelled `<select>` — the one form control the two sitting screens both need. */
export function FieldSelect({
  label,
  value,
  onChange,
  options,
  disabled = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-ink">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink disabled:bg-surface-raised disabled:text-ink-muted"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
