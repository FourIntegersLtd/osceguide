"use client";

import { boardChip, boardCardClipped, boardButtonSmall } from "@/foundation/ui/boardKit";
import { useId, type ReactNode } from "react";
import { Input, b2bTokens as t, cn } from "@/foundation/ui";
import type { Programme, SittingMode } from "@/domains/assess/api";
import type { Cohort } from "@/domains/assess/roster/api";
import { useAssessWords } from "@/capabilities/assess-words";

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
export type ProgrammeChoice = Pick<
  Programme,
  "id" | "exam_name" | "exam_code" | "status"
>;

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
  const w = useAssessWords();
  return (
    <fieldset className="flex flex-col gap-1.5" disabled={disabled}>
      <legend className="text-sm font-medium text-ink">Mode</legend>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {(
          [
            ["exam", "Exam", "Marked, signed off and released"],
            ["training", w.training, `Feedback straight to the ${w.trainee}`],
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
            <span className="text-osce-body font-medium text-b2b-headline">
              {label}
            </span>
            <span className="text-osce-meta text-b2b-mid">{blurb}</span>
          </button>
        ))}
      </div>
      <p className="text-sm text-ink-muted">
        {hint ??
          (value === "exam"
            ? `One candidate takes every station, up to twelve. You cannot add ${w.trainees} once it has started.`
            : `Each ${w.trainee} is paired with one station, and they rotate.`)}
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
  const w = useAssessWords();
  const selected = programmes.find((programme) => programme.id === value);
  return (
    <div className="flex flex-col gap-1.5">
      <FieldSelect
        label={w.hiring ? w.Exam : "Programme"}
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
          Marking and feedback follow the published marking scheme for{" "}
          {selected.exam_name}, so there is nothing else to choose.
        </p>
      ) : null}
    </div>
  );
}

/** The intake the sitting is held for. Optional: it is what lets deleting a cohort say how many sittings it detaches. */
export function CohortField({
  value,
  onChange,
  cohorts,
}: {
  value: string;
  onChange: (cohortId: string) => void;
  cohorts: Pick<Cohort, "id" | "name">[];
}) {
  return (
    <FieldSelect
      label="Year group"
      value={value}
      onChange={onChange}
      options={[
        { value: "", label: "None" },
        ...cohorts.map((c) => ({ value: c.id, label: c.name })),
      ]}
    />
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

/** The board's `.input`: 44px tall, 9px radius, 16px type. */
export const fieldInput =
  "box-border min-h-11 w-full rounded-board border border-osce-border bg-osce-surface px-3 text-[16px] text-ink disabled:bg-surface-raised disabled:text-ink-muted";

/** A label 8px above its control, and the helper line 8px below it (the assess form rhythm). */
export function Field({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: string;
  htmlFor?: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-2 block text-assess-label font-medium text-ink"
      >
        {label}
      </label>
      {children}
      {hint ? (
        <div
          id={htmlFor ? `${htmlFor}-hint` : undefined}
          className={cn(t.assessMeta, "mt-2")}
        >
          {hint}
        </div>
      ) : null}
    </div>
  );
}

/** A group of option cards drawn as radios: one title and one line each. */
export function OptionCards({
  label,
  options,
}: {
  label: string;
  options: {
    key: string;
    title: string;
    body: string;
    selected: boolean;
    onSelect: () => void;
  }[];
}) {
  return (
    <div role="radiogroup" aria-label={label} className={t.assessOptionStack}>
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          role="radio"
          aria-checked={option.selected}
          onClick={option.onSelect}
          className={cn(
            "box-border flex w-full items-start gap-3.5 rounded-osce-md border px-[18px] py-4 text-left text-ink",
            option.selected
              ? "border-osce-accent bg-osce-surface-inset"
              : "border-osce-border bg-osce-surface hover:bg-osce-canvas",
          )}
        >
          <span
            aria-hidden="true"
            className={cn(
              "mt-0.5 box-border h-[18px] w-[18px] shrink-0 rounded-full border",
              option.selected
                ? "border-[5px] border-osce-accent"
                : "border-border-strong",
            )}
          />
          <span>
            <span className="block text-osce-body font-medium">
              {option.title}
            </span>
            <span className={t.assessMeta}>{option.body}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

/** A labelled `<select>` — the one form control the two sitting screens both need. */
export function FieldSelect({
  label,
  value,
  onChange,
  options,
  disabled = false,
  hint,
  id,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  disabled?: boolean;
  hint?: ReactNode;
  id?: string;
}) {
  const fieldId = useId();
  return (
    <Field label={label} htmlFor={id ?? fieldId} hint={hint}>
      <select
        id={id ?? fieldId}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={fieldInput}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

const NOTES = {
  info: "bg-assess-chip-info-bg text-assess-chip-info-text",
  warn: "bg-osce-warning-bg text-osce-warning-text",
  ok: "bg-osce-success-bg text-osce-success-text",
} as const;

/** The board's `.note`: a tinted line that says how the page stands. */
export function Note({
  tone,
  children,
}: {
  tone: keyof typeof NOTES;
  children: ReactNode;
}) {
  return (
    <p
      role="status"
      className={cn(
        "rounded-osce-md px-3.5 py-3 text-assess-label leading-normal",
        NOTES[tone],
      )}
    >
      {children}
    </p>
  );
}

/** The board's `.chip`. */
export function Chip({
  tone,
  children,
}: {
  tone: "ok" | "warn" | "info";
  children: ReactNode;
}) {
  return <span className={boardChip(tone)}>{children}</span>;
}

/** The board's `.btn.sm`: 36px tall, secondary. */
export const smallButton = boardButtonSmall;
/** A card whose rows run edge to edge (the board's `.card.flush`). */
export const flushCard = boardCardClipped;
/** One row of a flush card (the board's `.row`). */
export const flushRow =
  "flex flex-wrap items-center gap-3.5 border-t border-osce-border-light px-5 py-3 text-assess-label first:border-t-0";
