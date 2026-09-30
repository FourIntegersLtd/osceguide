"use client";

import React from "react";
import { HiOutlineChevronDown } from "react-icons/hi2";
import { cn } from "@/foundation/ui/cn";
import { getInputClassName, type InputSize } from "@/foundation/ui/inputStyles";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  selectSize?: InputSize;
  invalid?: boolean;
  /** Renders a wrapped, labelled field rather than a bare select — same contract as `Input`. */
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
}

/**
 * The one dropdown. Painted with `getInputClassName` so a select sits beside
 * an `Input` in a form without a visible seam — the same surface, border,
 * focus treatment and sizes. Before this existed every screen hand-rolled its
 * own `<select>` chrome, which is how the console grew three different ones.
 */
export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      className,
      selectSize = "md",
      invalid = false,
      label,
      hint,
      error,
      id,
      children,
      ...props
    },
    ref,
  ) => {
    const reactId = React.useId();
    const selectId = id ?? reactId;
    const describedBy = error
      ? `${selectId}-error`
      : hint
        ? `${selectId}-hint`
        : undefined;
    const isInvalid = invalid || Boolean(error);

    // `className` sizes the whole field (the wrapper), so `w-auto` or `w-48`
    // behaves in a flex row the way it would on a plain element.
    const field = (
      <span className={cn("relative block w-full", className)}>
        <select
          ref={ref}
          id={selectId}
          aria-invalid={isInvalid || undefined}
          aria-describedby={describedBy}
          className={cn(
            getInputClassName({ size: selectSize, invalid: isInvalid }),
            "appearance-none pr-9",
          )}
          {...props}
        >
          {children}
        </select>
        <HiOutlineChevronDown
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle"
          aria-hidden
        />
      </span>
    );

    if (!label && !hint && !error) return field;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={selectId}
            className="text-osce-meta font-medium text-osce-ink-700"
          >
            {label}
          </label>
        )}
        {field}
        {error ? (
          <p
            id={`${selectId}-error`}
            className="text-osce-meta text-osce-danger-text"
          >
            {error}
          </p>
        ) : (
          hint && (
            <p
              id={`${selectId}-hint`}
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

Select.displayName = "Select";
