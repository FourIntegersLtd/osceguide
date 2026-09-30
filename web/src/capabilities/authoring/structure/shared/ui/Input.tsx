import React from "react";
import { cn } from "@/capabilities/authoring/structure/shared/lib/utils";

export type InputSize = "sm" | "md";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  inputSize?: InputSize;
  invalid?: boolean;
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
 * Focus is a single accent border. A ring on top of the border reads as a
 * double outline; keep `outline-none` paired with `focus:border-osce-accent`.
 */
export function getInputClassName({
  size = "md",
  invalid = false,
}: { size?: InputSize; invalid?: boolean } = {}) {
  return cn(
    "w-full rounded-osce-sm border bg-osce-surface text-ink",
    "placeholder:text-ink-subtle",
    "disabled:cursor-not-allowed disabled:bg-osce-canvas disabled:text-ink-muted",
    "focus:outline-none",
    invalid
      ? "border-osce-danger-border focus:border-osce-danger"
      : "border-osce-border focus:border-osce-accent",
    sizeClasses[size],
  );
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, inputSize = "md", invalid = false, type = "text", ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      aria-invalid={invalid || undefined}
      className={cn(getInputClassName({ size: inputSize, invalid }), className)}
      {...props}
    />
  ),
);

Input.displayName = "Input";
