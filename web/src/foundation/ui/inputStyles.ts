/**
 * Pure class-string composition for `Input`. Split out of `Input.tsx` the way
 * `buttonStyles.ts` is split out of `Button.tsx`, and for the same two
 * reasons: the node test runner can import it (it strips types but cannot
 * transform JSX), and a server component can call it — `productTokens.ts`
 * builds `b2cInputBase` from it at module scope, and a `"use client"` file
 * cannot be called from the server, only rendered.
 */
import { cn } from "@/foundation/ui/cn";

export type InputSize = "sm" | "md";

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
