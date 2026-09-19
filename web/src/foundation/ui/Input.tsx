import React from "react";
import { cn } from "@/foundation/ui/cn";

export type InputSize = "sm" | "md";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  inputSize?: InputSize;
  invalid?: boolean;
  /**
   * Renders a wrapped, labelled field rather than a bare input.
   *
   * A label associated by `htmlFor` is the difference between a field a screen
   * reader can announce and one it reads as "edit text", so making it a prop
   * rather than something each screen assembles is what keeps it from being
   * forgotten.
   */
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
}

/*
 * Taller below `sm` so a field clears the 44px touch minimum, denser from
 * `sm` up. `text-osce-body` is 16px by design — a smaller focused field
 * makes iOS Safari zoom the viewport — so do not step the size down here.
 */
const sizeClasses: Record<InputSize, string> = {
  sm: "px-3 py-2.5 sm:py-1.5 text-osce-body",
  md: "px-3 py-3 sm:py-2 text-osce-body",
};

/**
 * The canonical form control surface — `b2cInputBase` and `b2bInputBase` are
 * built from this, so inputs, selects and textareas match across the app and
 * the B2B workspace.
 *
 * The focus treatment is deliberate: `outline-none` on its own removes the
 * only focus indicator keyboard users have, so it is always paired with a
 * visible 2px ring. Do not reintroduce `focus:ring-0`.
 */
export function getInputClassName({
  size = "md",
  invalid = false,
}: { size?: InputSize; invalid?: boolean } = {}) {
  return cn(
    "w-full rounded-osce-sm border bg-osce-surface text-osce-ink-900",
    "placeholder:text-osce-ink-400",
    "disabled:cursor-not-allowed disabled:bg-osce-canvas disabled:text-osce-ink-500",
    "focus:outline-none focus:ring-2",
    invalid
      ? "border-osce-danger-border focus:border-osce-danger focus:ring-osce-danger-bg"
      : "border-osce-border focus:border-osce-accent focus:ring-osce-accent-subtle",
    sizeClasses[size],
  );
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    { className, inputSize = "md", invalid = false, type = "text", label, hint, error, id, ...props },
    ref,
  ) => {
    const reactId = React.useId();
    const inputId = id ?? reactId;
    const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
    const isInvalid = invalid || Boolean(error);

    const field = (
      <input
        ref={ref}
        id={inputId}
        type={type}
        aria-invalid={isInvalid || undefined}
        aria-describedby={describedBy}
        className={cn(getInputClassName({ size: inputSize, invalid: isInvalid }), className)}
        {...props}
      />
    );

    if (!label && !hint && !error) return field;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-osce-meta font-medium text-osce-ink-700">
            {label}
          </label>
        )}
        {field}
        {error ? (
          <p id={`${inputId}-error`} className="text-osce-meta text-osce-danger-text">
            {error}
          </p>
        ) : (
          hint && (
            <p id={`${inputId}-hint`} className="text-osce-meta text-b2c-text-muted">
              {hint}
            </p>
          )
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
