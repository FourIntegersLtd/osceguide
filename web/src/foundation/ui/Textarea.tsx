"use client";

import React from "react";
import { cn } from "@/foundation/ui/cn";
import { getInputClassName, type InputSize } from "@/foundation/ui/inputStyles";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  textareaSize?: InputSize;
  invalid?: boolean;
  /** Renders a wrapped, labelled field rather than a bare textarea — same contract as `Input`. */
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
}

/** The one multi-line field, painted exactly like `Input` so the two sit in a form without a seam. */
export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      textareaSize = "md",
      invalid = false,
      label,
      hint,
      error,
      id,
      rows = 3,
      ...props
    },
    ref,
  ) => {
    const reactId = React.useId();
    const fieldId = id ?? reactId;
    const describedBy = error
      ? `${fieldId}-error`
      : hint
        ? `${fieldId}-hint`
        : undefined;
    const isInvalid = invalid || Boolean(error);

    const field = (
      <textarea
        ref={ref}
        id={fieldId}
        rows={rows}
        aria-invalid={isInvalid || undefined}
        aria-describedby={describedBy}
        className={cn(
          getInputClassName({ size: textareaSize, invalid: isInvalid }),
          className,
        )}
        {...props}
      />
    );

    if (!label && !hint && !error) return field;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={fieldId}
            className="text-osce-meta font-medium text-osce-ink-700"
          >
            {label}
          </label>
        )}
        {field}
        {error ? (
          <p
            id={`${fieldId}-error`}
            className="text-osce-meta text-osce-danger-text"
          >
            {error}
          </p>
        ) : (
          hint && (
            <p
              id={`${fieldId}-hint`}
              className="text-osce-meta text-ink-subtle"
            >
              {hint}
            </p>
          )
        )}
      </div>
    );
  },
);

Textarea.displayName = "Textarea";
