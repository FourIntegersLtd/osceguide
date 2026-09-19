"use client";

import React from "react";
import { cn } from "@/foundation/ui/cn";
import { getInputClassName, type InputSize } from "@/foundation/ui/inputStyles";

export type { InputSize } from "@/foundation/ui/inputStyles";
export { getInputClassName } from "@/foundation/ui/inputStyles";

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