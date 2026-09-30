"use client";

import { useId, type ReactNode } from "react";
import { HiOutlineArrowDown, HiOutlineArrowUp, HiOutlineTrash } from "react-icons/hi2";
import { cn, getInputClassName } from "@/foundation/ui";
import { useRubricBuilder } from "@/capabilities/authoring/rubrics/builderContext";
import { getAt, moveItem, pathText, removeItem, setAt, type JsonPath } from "@/capabilities/authoring/rubrics/jsonPath";
import { problemsAt } from "@/capabilities/authoring/rubrics/problems";
import { textAt } from "@/capabilities/authoring/rubrics/rubricEdits";
import type { Choice } from "@/capabilities/authoring/rubrics/rubricVocabulary";

/**
 * The inputs the rubric builder is made of. Each one is bound to a path in the
 * draft structure: it reads its value there, writes it back there, and shows
 * under itself any problem the backend reported at exactly that path. The
 * `data-path` attribute is what the problem list scrolls to.
 */

const labelClass = "block text-osce-meta font-medium text-osce-ink-500";
const hintClass = "mt-0.5 text-osce-caption text-osce-ink-400";

/** The backend's messages about one input, in the danger colour under it. */
export function ProblemNote({ messages }: { messages: readonly string[] }) {
  if (messages.length === 0) return null;
  return (
    <ul className="mt-1 space-y-0.5" role="alert">
      {messages.map((message) => (
        <li key={message} className="text-osce-caption text-osce-danger">
          {message}
        </li>
      ))}
    </ul>
  );
}

/** A label, the input, an optional hint and the input's problems. */
function Labelled({
  inputId,
  label,
  hint,
  messages,
  className,
  children,
}: {
  inputId: string;
  label: string;
  hint?: string;
  messages: readonly string[];
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <label htmlFor={inputId} className={labelClass}>
        {label}
      </label>
      <div className="mt-1">{children}</div>
      {hint ? <p className={hintClass}>{hint}</p> : null}
      <ProblemNote messages={messages} />
    </div>
  );
}

/** Text at a path: a one-line input, or a textarea when `rows` is given. */
export function TextAtPath({
  path,
  label,
  hint,
  placeholder,
  rows,
  mono = false,
  className,
}: {
  path: JsonPath;
  label: string;
  hint?: string;
  placeholder?: string;
  rows?: number;
  mono?: boolean;
  className?: string;
}) {
  const { structure, edit, problems, readOnly } = useRubricBuilder();
  const inputId = useId();
  const messages = problemsAt(problems, path);
  const shared = {
    id: inputId,
    "data-path": pathText(path),
    value: textAt(structure, path),
    placeholder,
    readOnly,
    onChange: (event: { target: { value: string } }) => {
      const value = event.target.value;
      edit((current) => setAt(current, path, value));
    },
    className: cn(getInputClassName({ size: "sm", invalid: messages.length > 0 }), mono && "font-mono"),
  };
  return (
    <Labelled inputId={inputId} label={label} hint={hint} messages={messages} className={className}>
      {rows ? <textarea rows={rows} {...shared} className={cn(shared.className, "py-2")} /> : <input type="text" {...shared} />}
    </Labelled>
  );
}

/** A number at a path. Clearing the box removes the key, so the backend's default applies. */
export function NumberAtPath({
  path,
  label,
  hint,
  step = "any",
  className,
}: {
  path: JsonPath;
  label: string;
  hint?: string;
  step?: string;
  className?: string;
}) {
  const { structure, edit, problems, readOnly } = useRubricBuilder();
  const inputId = useId();
  const messages = problemsAt(problems, path);
  const value = getAt(structure, path);
  return (
    <Labelled inputId={inputId} label={label} hint={hint} messages={messages} className={className}>
      <input
        id={inputId}
        data-path={pathText(path)}
        type="number"
        step={step}
        readOnly={readOnly}
        value={typeof value === "number" ? value : ""}
        onChange={(event) => {
          const text = event.target.value;
          edit((current) => setAt(current, path, text === "" ? undefined : Number(text)));
        }}
        className={getInputClassName({ size: "sm", invalid: messages.length > 0 })}
      />
    </Labelled>
  );
}

/** One of a list of choices at a path; `emptyLabel` offers "none", which removes the key. */
export function SelectAtPath<Value extends string>({
  path,
  label,
  hint,
  choices,
  emptyLabel,
  onPick,
  className,
}: {
  path: JsonPath;
  label: string;
  hint?: string;
  choices: readonly Choice<Value>[];
  emptyLabel?: string;
  /** Replace the plain write, for a choice that changes more than its own key. */
  onPick?: (value: Value) => void;
  className?: string;
}) {
  const { structure, edit, problems, readOnly } = useRubricBuilder();
  const inputId = useId();
  const messages = problemsAt(problems, path);
  const value = getAt(structure, path);
  const selected = choices.find((choice) => choice.value === value);
  return (
    <Labelled inputId={inputId} label={label} hint={hint ?? selected?.hint} messages={messages} className={className}>
      <select
        id={inputId}
        data-path={pathText(path)}
        disabled={readOnly}
        value={typeof value === "string" ? value : ""}
        onChange={(event) => {
          const picked = event.target.value;
          if (picked === "") {
            edit((current) => setAt(current, path, undefined));
            return;
          }
          if (onPick) onPick(picked as Value);
          else edit((current) => setAt(current, path, picked));
        }}
        className={getInputClassName({ size: "sm", invalid: messages.length > 0 })}
      >
        {emptyLabel !== undefined || !selected ? <option value="">{emptyLabel ?? "Choose…"}</option> : null}
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    </Labelled>
  );
}

/**
 * A yes/no at a path. `whenOff` is what "no" stores: most switches default to
 * off, so "no" removes the key; `required` defaults to on, so "no" stores false.
 */
export function ToggleAtPath({
  path,
  label,
  hint,
  defaultOn = false,
}: {
  path: JsonPath;
  label: string;
  hint?: string;
  defaultOn?: boolean;
}) {
  const { structure, edit, problems, readOnly } = useRubricBuilder();
  const value = getAt(structure, path);
  const checked = typeof value === "boolean" ? value : defaultOn;
  return (
    <div>
      <label className="flex items-start gap-2 text-osce-meta text-osce-ink-900">
        <input
          type="checkbox"
          data-path={pathText(path)}
          disabled={readOnly}
          checked={checked}
          onChange={(event) => {
            const next = event.target.checked;
            // Store only a value that differs from the backend's default.
            edit((current) => setAt(current, path, next === defaultOn ? undefined : next));
          }}
          className="mt-0.5 h-4 w-4 rounded border-osce-border accent-osce-accent"
        />
        <span>
          <span className="font-medium">{label}</span>
          {hint ? <span className="block text-osce-caption text-osce-ink-400">{hint}</span> : null}
        </span>
      </label>
      <ProblemNote messages={problemsAt(problems, path)} />
    </div>
  );
}

/** Move up, move down and remove, for one item in a list. */
export function ItemControls({ listPath, index, count, noun }: { listPath: JsonPath; index: number; count: number; noun: string }) {
  const { edit, readOnly } = useRubricBuilder();
  if (readOnly) return null;
  const buttonClass =
    "rounded-osce-sm p-1.5 text-osce-ink-400 hover:bg-osce-canvas hover:text-osce-ink-900 disabled:opacity-30 disabled:hover:bg-transparent";
  return (
    <div className="flex shrink-0 items-center gap-0.5">
      <button type="button" className={buttonClass} aria-label={`Move ${noun} up`} disabled={index === 0} onClick={() => edit((current) => moveItem(current, [...listPath, index], -1))}>
        <HiOutlineArrowUp className="h-4 w-4" aria-hidden />
      </button>
      <button type="button" className={buttonClass} aria-label={`Move ${noun} down`} disabled={index === count - 1} onClick={() => edit((current) => moveItem(current, [...listPath, index], 1))}>
        <HiOutlineArrowDown className="h-4 w-4" aria-hidden />
      </button>
      <button type="button" className={cn(buttonClass, "hover:text-osce-danger")} aria-label={`Remove ${noun}`} onClick={() => edit((current) => removeItem(current, [...listPath, index]))}>
        <HiOutlineTrash className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}

/** A dashed "add" button; hidden on a read-only version. */
export function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  const { readOnly } = useRubricBuilder();
  if (readOnly) return null;
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-osce-sm border border-dashed border-osce-border px-3 py-1.5 text-osce-meta font-medium text-osce-ink-500 hover:border-osce-accent hover:text-osce-accent"
    >
      + {label}
    </button>
  );
}

/** A small uppercase heading inside a card. */
export function GroupHeading({ children, count }: { children: ReactNode; count?: number }) {
  return (
    <p className="text-osce-caption font-semibold uppercase tracking-wide text-osce-ink-400">
      {children}
      {count !== undefined ? <span className="ml-1 text-osce-ink-400">· {count}</span> : null}
    </p>
  );
}
