"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { examDateFieldLabel, examinerTipsLabel } from "@/capabilities/authoring/lib/authoringCopy";
import type { ReactNode } from "react";
import { Checkbox, getInputClassName, Textarea, FoldSection, b2bTokens } from "@/foundation/ui";
import { BoardCheckbox, BoardTextarea } from "@/foundation/ui/BoardFields";
import { boardInput } from "@/foundation/ui/boardKit";
import type { ExamSettings } from "@/capabilities/authoring/api";

type SessionMode = NonNullable<ExamSettings["session_modes"]>[number];
type HelpMode = NonNullable<ExamSettings["help_modes"]>[number];

const SESSION_MODES: { mode: SessionMode; label: string }[] = [
  { mode: "debrief", label: "Tutor debrief" },
  { mode: "practice_as_patient", label: "Practise as the patient" },
];
const HELP_MODES: { mode: HelpMode; label: string }[] = [
  { mode: "navigate", label: "Show me where things are" },
  { mode: "knowledge_base", label: "Answer questions from our guides" },
];
type PromptField =
  "station_prompt_text" | "summary_prompt_text" | "blog_prompt_text";
const PROMPTS: {
  field: PromptField;
  label: string;
  keyOf: "station_prompt" | "summary_prompt" | "blog_prompt";
}[] = [
  {
    field: "station_prompt_text",
    label: "Instructions for writing stations",
    keyOf: "station_prompt",
  },
  {
    field: "summary_prompt_text",
    label: "Instructions for condition summaries",
    keyOf: "summary_prompt",
  },
  { field: "blog_prompt_text", label: "Instructions for blog posts", keyOf: "blog_prompt" },
];

/** Adds or removes one value of a multi-choice setting, keeping the list's order. */
function toggled<T>(list: readonly T[] | undefined, item: T, on: boolean): T[] {
  const rest = (list ?? []).filter((existing) => existing !== item);
  return on ? [...rest, item] : rest;
}

/**
 * How this exam differs apart from its rubric (`exams.settings`). Folded away
 * by default: a new exam works on the defaults, and these are for the exam
 * that needs to say otherwise.
 */
export function ExamSettingsFields({
  value,
  onChange,
  title = "Exam settings",
  description,
  bare = false,
  lead,
  board = false,
}: {
  value: ExamSettings;
  onChange: (patch: Partial<ExamSettings>) => void;
  title?: string;
  description?: string;
  /** The board's quiet disclosure (a divider and a plain summary) instead of the folded card. */
  bare?: boolean;
  /** A control that opens the disclosure, before the settings. */
  lead?: ReactNode;
  /** The ExamSettings board's open card: bare fields stacked under the summary, no gaps (the board's `.in`). */
  board?: boolean;
}) {
  const w = useAssessWords();
  const generation: Partial<NonNullable<ExamSettings["generation"]>> =
    value.generation ?? {};
  const setPrompt = (field: PromptField, text: string) =>
    onChange({
      generation: {
        ...generation,
        [field]: text.trim() === "" ? null : text,
      } as ExamSettings["generation"],
    });

  const fields = (
      <div className={board ? "flex flex-col leading-[1.6]" : "space-y-4"}>
        {lead}
        <Field board={board} label={examDateFieldLabel(w)}>
          <input
            value={value.date_label ?? ""}
            maxLength={40}
            onChange={(e) => onChange({ date_label: e.target.value })}
            className={board ? boardInput : `mt-1 ${getInputClassName()}`}
            placeholder="Exam date"
          />
        </Field>
        <CheckboxGroup
          board={board}
          label="After a station"
          options={SESSION_MODES.map(({ mode, label }) => ({
            label,
            checked: (value.session_modes ?? []).includes(mode),
            onChange: (on: boolean) =>
              onChange({
                session_modes: toggled(value.session_modes, mode, on),
              }),
          }))}
        />
        <CheckboxGroup
          board={board}
          label="Help panel"
          options={HELP_MODES.map(({ mode, label }) => ({
            label,
            checked: (value.help_modes ?? []).includes(mode),
            onChange: (on: boolean) =>
              onChange({ help_modes: toggled(value.help_modes, mode, on) }),
          }))}
        />
        <CheckboxGroup
          board={board}
          label="Other"
          options={[
            {
              label: examinerTipsLabel(w),
              checked: value.show_tips_while_marking ?? false,
              onChange: (on: boolean) =>
                onChange({ show_tips_while_marking: on }),
            },
            {
              label: "Email people waiting for a peer partner",
              checked: value.peer_waiting_email ?? false,
              onChange: (on: boolean) => onChange({ peer_waiting_email: on }),
            },
          ]}
        />
        {PROMPTS.map(({ field, label, keyOf }) => (
          <Field key={field} board={board} label={label}>
            {board ? (
              <BoardTextarea
                value={generation[field] ?? ""}
                maxLength={20000}
                rows={4}
                onChange={(e) => setPrompt(field, e.target.value)}
                className="min-h-20"
                placeholder={`Blank uses the built-in prompt (${generation[keyOf] ?? `generic.${keyOf.replace("_prompt", "")}`}).`}
              />
            ) : (
              <Textarea
                value={generation[field] ?? ""}
                maxLength={20000}
                rows={4}
                onChange={(e) => setPrompt(field, e.target.value)}
                className="mt-1"
                placeholder={`Blank uses the built-in prompt (${generation[keyOf] ?? `generic.${keyOf.replace("_prompt", "")}`}).`}
              />
            )}
          </Field>
        ))}
      </div>
  );
  if (board) {
    return (
      <FoldSection board title={title} description={description} defaultOpen={false}>
        {fields}
      </FoldSection>
    );
  }
  if (bare) {
    return (
      <details className="border-t border-osce-border-light pt-3.5">
        <summary className="min-h-8 cursor-pointer text-assess-label font-medium text-ink">{title}</summary>
        {description ? <div className="mt-2 text-assess-meta text-ink-subtle">{description}</div> : null}
        <div className="mt-4">{fields}</div>
      </details>
    );
  }
  return (
    <FoldSection title={title} description={description} defaultOpen={false}>
      {fields}
    </FoldSection>
  );
}

function CheckboxGroup({
  label,
  options,
  board = false,
}: {
  board?: boolean;
  label: string;
  options: {
    label: string;
    checked: boolean;
    onChange: (on: boolean) => void;
  }[];
}) {
  if (board) {
    return (
      <fieldset className="m-0 border-0 p-0">
        <legend className={`mb-1 p-0 ${b2bTokens.assessEyebrow}`}>{label}</legend>
        {options.map((option) => (
          <BoardCheckbox
            key={option.label}
            label={option.label}
            checked={option.checked}
            onChange={(e) => option.onChange(e.target.checked)}
          />
        ))}
      </fieldset>
    );
  }
  return (
    <fieldset>
      <legend className="text-osce-body font-semibold text-ink">
        {label}
      </legend>
      <div className="mt-1 flex flex-wrap gap-x-5 gap-y-1">
        {options.map((option) => (
          <Checkbox
            key={option.label}
            checked={option.checked}
            onChange={(e) => option.onChange(e.target.checked)}
            label={option.label}
            className="items-center"
          />
        ))}
      </div>
    </fieldset>
  );
}

export function Field({
  label,
  children,
  board = false,
}: {
  label: string;
  children: React.ReactNode;
  /** The board's label: 14px medium, 6px above its control. */
  board?: boolean;
}) {
  // The label wraps its one control, so the control is named by it.
  if (board) {
    return (
      <label className="flex flex-col gap-1.5">
        <span className="block text-assess-label font-medium text-ink">{label}</span>
        {children}
      </label>
    );
  }
  return (
    <label className="flex flex-col gap-1">
      <span className="block text-osce-body font-semibold text-ink">{label}</span>
      {children}
    </label>
  );
}
