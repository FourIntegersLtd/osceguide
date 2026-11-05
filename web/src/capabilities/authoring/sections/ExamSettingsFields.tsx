"use client";

import { Checkbox, getInputClassName, Textarea, FoldSection } from "@/foundation/ui";
import type { ExamSettings } from "@/capabilities/authoring/api";

type SessionMode = NonNullable<ExamSettings["session_modes"]>[number];
type HelpMode = NonNullable<ExamSettings["help_modes"]>[number];

const SESSION_MODES: { mode: SessionMode; label: string }[] = [
  { mode: "debrief", label: "Tutor debrief" },
  { mode: "practice_as_patient", label: "Practise as the patient" },
];
const HELP_MODES: { mode: HelpMode; label: string }[] = [
  { mode: "navigate", label: "Find screens" },
  { mode: "knowledge_base", label: "Answer from the knowledge base" },
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
    label: "Station writing prompt",
    keyOf: "station_prompt",
  },
  {
    field: "summary_prompt_text",
    label: "Condition summary prompt",
    keyOf: "summary_prompt",
  },
  { field: "blog_prompt_text", label: "Blog prompt", keyOf: "blog_prompt" },
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
}: {
  value: ExamSettings;
  onChange: (patch: Partial<ExamSettings>) => void;
  title?: string;
  description?: string;
}) {
  const generation: Partial<NonNullable<ExamSettings["generation"]>> =
    value.generation ?? {};
  const setPrompt = (field: PromptField, text: string) =>
    onChange({
      generation: {
        ...generation,
        [field]: text.trim() === "" ? null : text,
      } as ExamSettings["generation"],
    });

  return (
    <FoldSection title={title} description={description} defaultOpen={false}>
      <div className="space-y-4">
        <Field label="Date label">
          <input
            value={value.date_label ?? ""}
            maxLength={40}
            onChange={(e) => onChange({ date_label: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="Exam date"
          />
        </Field>
        <CheckboxGroup
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
          label="Help dock"
          options={HELP_MODES.map(({ mode, label }) => ({
            label,
            checked: (value.help_modes ?? []).includes(mode),
            onChange: (on: boolean) =>
              onChange({ help_modes: toggled(value.help_modes, mode, on) }),
          }))}
        />
        <CheckboxGroup
          label="Other"
          options={[
            {
              label: "Show examiner tips while marking",
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
          <Field key={field} label={label}>
            <Textarea
              value={generation[field] ?? ""}
              maxLength={20000}
              rows={4}
              onChange={(e) => setPrompt(field, e.target.value)}
              className="mt-1"
              placeholder={`Blank uses the built-in prompt (${generation[keyOf] ?? `generic.${keyOf.replace("_prompt", "")}`}).`}
            />
          </Field>
        ))}
      </div>
    </FoldSection>
  );
}

function CheckboxGroup({
  label,
  options,
}: {
  label: string;
  options: {
    label: string;
    checked: boolean;
    onChange: (on: boolean) => void;
  }[];
}) {
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
}: {
  label: string;
  children: React.ReactNode;
}) {
  // The label wraps its one control, so the control is named by it.
  return (
    <label className="block">
      <span className="block text-osce-body font-semibold text-ink">{label}</span>
      {children}
    </label>
  );
}
