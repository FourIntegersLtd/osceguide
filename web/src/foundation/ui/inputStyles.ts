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
 * Focus is a single light-blue border, set for every text field in
 * `globals.css` (`--osce-focus-border`). A ring on top of the border reads as
 * a double outline.
 */
export function getInputClassName({
  size = "md",
  invalid = false,
}: { size?: InputSize; invalid?: boolean } = {}) {
  return cn(
    "w-full rounded-control border bg-osce-surface text-osce-ink-900",
    "placeholder:text-osce-ink-400",
    "disabled:cursor-not-allowed disabled:bg-osce-canvas disabled:text-osce-ink-500",
    "focus:outline-none",
    invalid
      ? "border-osce-danger-border focus:border-osce-danger"
      : "border-osce-border focus:border-osce-accent",
    sizeClasses[size],
  );
}

/**
 * A search box with a magnifying glass drawn inside its left edge.
 *
 * The left padding leaves room for the icon, and the browser's own clear
 * button is hidden so it does not sit on top of anything placed on the right.
 */
export const iconSearchInputClassName =
  "w-full appearance-none rounded-control border border-b2c-border bg-osce-surface py-2 pl-10 pr-3 text-osce-body text-osce-ink-900 outline-none placeholder:text-osce-ink-400 focus:border-osce-accent focus:bg-osce-surface focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden";
