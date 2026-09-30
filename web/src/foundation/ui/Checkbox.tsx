"use client";

import React from "react";
import { cn } from "@/foundation/ui/cn";

export interface CheckboxProps extends Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "type"
> {
  label: React.ReactNode;
  /** A second, quieter line under the label for what ticking it actually does. */
  description?: React.ReactNode;
}

/** A labelled checkbox — the whole row is the hit target, ticked in the skin's accent. */
export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, className, id, disabled, ...props }, ref) => {
    const reactId = React.useId();
    const fieldId = id ?? reactId;
    return (
      <label
        htmlFor={fieldId}
        className={cn(
          "flex items-start gap-3",
          disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
          className,
        )}
      >
        <input
          ref={ref}
          id={fieldId}
          type="checkbox"
          disabled={disabled}
          className="mt-0.5 h-4 w-4 shrink-0 rounded-osce-sm border-border accent-accent"
          {...props}
        />
        <span className="min-w-0">
          <span className="block text-osce-data text-ink">{label}</span>
          {description ? (
            <span className="block text-osce-meta text-ink-subtle">
              {description}
            </span>
          ) : null}
        </span>
      </label>
    );
  },
);

Checkbox.displayName = "Checkbox";
