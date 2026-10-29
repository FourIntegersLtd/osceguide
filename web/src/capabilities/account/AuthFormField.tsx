import { ChangeEvent, ReactNode } from "react";
import { LuLock, LuMail, LuUser } from "react-icons/lu";
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
  /** The icon inside the left edge of the box. */
  icon?: FieldIcon;
};

const errorRing = "border-osce-danger focus:border-osce-danger";

const FIELD_ICONS = { mail: LuMail, lock: LuLock, user: LuUser } as const;
type FieldIcon = keyof typeof FIELD_ICONS;

/** An email field shows a letter and a password field a lock, unless the caller names another. */
function defaultIcon(type: string, name: string): FieldIcon | null {
  if (type === "email") return "mail";
  if (/password/i.test(name)) return "lock";
  return null;
}

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
  icon,
}: AuthFormFieldProps) {
  const iconName = icon ?? (fieldType === "select" ? null : defaultIcon(type, name));
  const LeadingIcon = iconName ? FIELD_ICONS[iconName] : null;
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
          className={cn(authInput, "pl-3.5", error ? errorRing : undefined)}
        >
          {options?.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <div className="relative">
          {LeadingIcon ? (
            <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-site-faint" aria-hidden="true">
              <LeadingIcon className="h-[18px] w-[18px]" />
            </span>
          ) : null}
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
              LeadingIcon ? "pl-[42px]" : "pl-3.5",
              suffix ? "pr-10" : undefined,
              error ? errorRing : undefined,
            )}
          />
          {suffix}
        </div>
      )}
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-osce-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-[13px] text-site-faint">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
