import { ChangeEvent, ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import { Input } from "@/foundation/ui";
import { authInput, authLabel } from "@/foundation/ui/authTheme";

type SelectOption = {
  value: string;
  label: string;
};

type AuthFormFieldProps = {
  label: string;
  name: string;
  type?: React.HTMLInputTypeAttribute;
  value: string;
  onChange: (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void;
  required?: boolean;
  autoComplete?: string;
  id?: string;
  fieldType?: "input" | "select";
  options?: SelectOption[];
  suffix?: ReactNode;
  className?: string;
  /** Inline validation message; sets aria-invalid and a red border. */
  error?: string | null;
  /** Persistent helper text under the field (e.g. password rules). */
  hint?: string;
};

const errorRing = "border-osce-danger focus:ring-osce-danger/30";

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
  error,
  hint,
}: AuthFormFieldProps) {
  const fieldId = id ?? name;
  const errorId = `${fieldId}-error`;
  const hintId = `${fieldId}-hint`;
  const describedBy =
    [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ") ||
    undefined;

  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={fieldId} className={authLabel}>
        {label}
      </label>
      {fieldType === "select" ? (
        <select
          id={fieldId}
          name={name}
          value={value}
          onChange={onChange}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(authInput, error ? errorRing : undefined)}
        >
          {options?.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <div className="relative">
          <Input
            id={fieldId}
            type={type}
            name={name}
            value={value}
            onChange={onChange}
            required={required}
            autoComplete={autoComplete}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            className={cn(
              authInput,
              suffix ? "pr-10" : undefined,
              error ? errorRing : undefined,
            )}
          />
          {suffix}
        </div>
      )}
      {error ? (
        <p id={errorId} role="alert" className="text-osce-meta text-osce-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-osce-meta text-b2c-text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
