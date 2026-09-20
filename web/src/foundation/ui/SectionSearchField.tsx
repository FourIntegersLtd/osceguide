"use client";

import type { FormEvent, ReactNode } from "react";
import { getInputClassName } from "@/foundation/ui/inputStyles";
import { cn } from "@/foundation/ui/cn";

/**
 * Section toolbar search — sits on the page canvas (no card), aligned right.
 */
export function SectionSearchField({
  value,
  onChange,
  placeholder,
  ariaLabel,
  className,
  maxWidthClass = "max-w-md",
  onSubmit,
  trailing,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  ariaLabel?: string;
  className?: string;
  maxWidthClass?: string;
  /** When set, wraps the field in a form and runs on Enter / implicit submit. */
  onSubmit?: () => void;
  trailing?: ReactNode;
}) {
  const label = ariaLabel ?? placeholder;

  const input = (
    <input
      type="search"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      aria-label={label}
      className={getInputClassName()}
    />
  );

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit?.();
  };

  return (
    <div className={cn("flex w-full justify-end", className)}>
      {onSubmit || trailing ? (
        <form
          className={cn("flex w-full items-center gap-2", maxWidthClass)}
          onSubmit={handleSubmit}
          role="search"
        >
          <label className="min-w-0 flex-1">
            <span className="sr-only">{label}</span>
            {input}
          </label>
          {trailing}
        </form>
      ) : (
        <label className={cn("relative block w-full", maxWidthClass)}>
          <span className="sr-only">{label}</span>
          {input}
        </label>
      )}
    </div>
  );
}
