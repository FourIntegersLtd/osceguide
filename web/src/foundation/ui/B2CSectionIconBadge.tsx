import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import { b2cSectionIconChipBase } from "@/foundation/ui/productTokens";

/**
 * Icon tile (canvas `.tile`). Quiet by default: a grey tile with body ink.
 * Only the status tones (emerald, amber, rose) keep colour, because there
 * the colour is the message. The decorative hues all render neutral.
 */
export type B2CSectionIconTone =
  | "primary"
  | "emerald"
  | "amber"
  | "rose"
  | "violet"
  | "sky"
  | "orange";

const toneClass: Record<B2CSectionIconTone, string> = {
  primary: "bg-osce-accent-muted text-osce-ink-700",
  emerald: "bg-osce-success-bg text-osce-success-text",
  amber: "bg-osce-warning-bg text-osce-warning-text",
  rose: "bg-osce-danger-bg text-osce-danger-text",
  violet: "bg-osce-accent-muted text-osce-ink-700",
  sky: "bg-osce-accent-muted text-osce-ink-700",
  orange: "bg-osce-accent-muted text-osce-ink-700",
};

const sizeClass = {
  xs: "h-6 w-6 [&>svg]:h-3.5 [&>svg]:w-3.5",
  sm: "h-8 w-8 [&>svg]:h-4 [&>svg]:w-4",
  md: "h-9 w-9 [&>svg]:h-[18px] [&>svg]:w-[18px]",
  lg: "h-10 w-10 [&>svg]:h-5 [&>svg]:w-5",
} as const;

export type B2CSectionIconBadgeSize = keyof typeof sizeClass;

export function B2CSectionIconBadge({
  tone = "primary",
  size = "sm",
  children,
  className = "",
}: {
  tone?: B2CSectionIconTone;
  size?: B2CSectionIconBadgeSize;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        b2cSectionIconChipBase,
        sizeClass[size],
        toneClass[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
