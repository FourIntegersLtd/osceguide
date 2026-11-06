import type { ChangeEvent, ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import { boardInput, boardLabel } from "@/foundation/ui/boardKit";

type SelectOption = {
  value: string;
  label: string;
};

type FieldElement = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

type AuthFormFieldProps = {
  label: string;
  name: string;
  type?: React.HTMLInputTypeAttribute;
  value: string;
  /** Method syntax: callers handle the element their field is (an input, or a select), and a handler for one is accepted. */
  onChange(event: ChangeEvent<FieldElement>): void;
  required?: boolean;
  autoComplete?: string;
  id?: string;
  fieldType?: "input" | "select" | "textarea";
  options?: SelectOption[];
  suffix?: ReactNode;
  className?: string;
  maxLength?: number;
  /** Inline validation message; sets aria-invalid and a red border. */
  error?: string | null;
  /** Persistent helper text under the field (e.g. password rules). */
  hint?: string;
  /** The board draws some boxes with a placeholder only; the label text becomes the placeholder and the label stays for screen readers and password managers. */
  hideLabel?: boolean;
};

const errorRing = "border-osce-danger-text";
/** The board's `.input` with the assess skin's quiet light-blue focus (1px, never the saturated accent). */
const field = `${boardInput} focus:border-assess-select-border focus:outline-none focus:ring-4 focus:ring-assess-focus-ring`;

/** One labelled box of a sign-in form: the board's `<div><label/><input/><div class="hint"/></div>`. */
export default function AuthFormField({
  label,
  name,
  type = "text",
  value,
  onChange,
  required,
  autoComplete,
  id,
  fieldType = "input",
  options,
  suffix,
  className,
  maxLength,
  error,
  hint,
  hideLabel,
}: AuthFormFieldProps) {
  const fieldId = id ?? name;
  const errorId = `${fieldId}-error`;
  const hintId = `${fieldId}-hint`;
  const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ") || undefined;
  const shared = {
    id: fieldId,
    name,
    value,
    onChange,
    required,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy,
    placeholder: hideLabel ? label : undefined,
  } as const;
  const boxed = cn(field, error ? errorRing : undefined);

  return (
    <div className={className}>
      <label htmlFor={fieldId} className={hideLabel ? "sr-only" : boardLabel}>
        {label}
      </label>
      {fieldType === "select" ? (
        <select {...shared} className={boxed}>
          {options?.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : fieldType === "textarea" ? (
        <textarea {...shared} maxLength={maxLength} className={cn(boxed, "min-h-24 resize-y py-2.5")} />
      ) : (
        <div className="relative">
          <input {...shared} type={type} autoComplete={autoComplete} className={cn(boxed, suffix ? "pr-10" : undefined)} />
          {suffix}
        </div>
      )}
      {error ? (
        <p id={errorId} role="alert" className="mt-1.5 text-assess-meta leading-normal text-osce-danger-text">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="mt-1.5 text-assess-meta leading-normal text-osce-ink-500">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
