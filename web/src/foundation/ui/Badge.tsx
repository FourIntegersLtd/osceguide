import React from "react";
import { cn } from "@/foundation/ui/cn";

export type BadgeVariant =
  | "neutral"
  | "default"
  | "success"
  | "warning"
  | "danger"
  | "info"
  // The accent blue, under the name the newer screens use for it. Same pill as
  // `info`; kept as its own name so a screen can say what it means.
  | "accent"
  | "purple";

/** The newer screens say `tone` where the ported ones say `variant`. */
export type BadgeTone = BadgeVariant;

export type BadgeSize = "xs" | "sm";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  /**
   * The same thing as `variant`, under the name the newer screens use.
   *
   * Two words for one idea is worse than one, but renaming every call site in
   * both directions during a port is how a port stalls. `variant` is the
   * older and more widely used spelling, so it wins when both are given.
   */
  tone?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
}

/**
 * Status pill. One semantic palette for the whole product — a "success"
 * badge is the same green in the app and in the B2B workspace, so there is
 * no theme switch here.
 */
const variantClasses: Record<BadgeVariant, string> = {
  neutral: "bg-osce-canvas text-osce-ink-700 border-osce-border",
  default: "bg-osce-canvas text-osce-ink-700 border-osce-border",
  success:
    "bg-osce-success-bg text-osce-success-text border-osce-success-border",
  warning:
    "bg-osce-warning-bg text-osce-warning-text border-osce-warning-border",
  danger: "bg-osce-danger-bg text-osce-danger-text border-osce-danger-border",
  info: "bg-osce-info-bg text-osce-info-text border-osce-info-border",
  accent: "bg-osce-accent-subtle text-osce-accent border-osce-accent-muted",
  /** Reuses the reasoning reading tone, so the palette stays closed. */
  purple:
    "bg-osce-tone-reasoning-header text-osce-tone-reasoning-text border-osce-tone-reasoning-border",
};

const dotClasses: Record<BadgeVariant, string> = {
  neutral: "bg-osce-ink-400",
  default: "bg-osce-ink-400",
  success: "bg-osce-success-icon",
  warning: "bg-osce-warning-icon",
  danger: "bg-osce-danger-icon",
  info: "bg-osce-info-icon",
  accent: "bg-osce-accent",
  purple: "bg-osce-tone-reasoning-text",
};

const sizeClasses: Record<BadgeSize, string> = {
  xs: "px-1.5 py-0.5 text-osce-caption",
  sm: "px-2.5 py-0.5 text-osce-caption",
};

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    { className, variant, tone, size = "sm", dot = false, children, ...props },
    ref,
  ) => {
    const resolved = variant ?? tone ?? "neutral";
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1 rounded-full border font-semibold",
          variantClasses[resolved],
          sizeClasses[size],
          className,
        )}
        {...props}
      >
        {dot && (
          <span
            className={cn("h-1.5 w-1.5 shrink-0 rounded-full", dotClasses[resolved])}
            aria-hidden="true"
          />
        )}
        {children}
      </span>
    );
  },
);

Badge.displayName = "Badge";
