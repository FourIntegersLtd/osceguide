import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";

export type AlertTone = "info" | "success" | "warning" | "danger";

const TONES: Record<AlertTone, string> = {
  info: "bg-accent-subtle border-accent/25 text-ink",
  success: "bg-success-subtle border-success/25 text-ink",
  warning: "bg-warning-subtle border-warning/25 text-ink",
  danger: "bg-danger-subtle border-danger/25 text-ink",
};

/**
 * Transient and inline messages both land here, so a failure never renders as
 * "no data" and never as a `window.alert`. Both were findings in the consumer
 * UX audit; one component is how they stay fixed.
 */
export function Alert({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: AlertTone;
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn("rounded-panel border px-4 py-3 text-sm", TONES[tone], className)}
    >
      {title && <p className="font-semibold">{title}</p>}
      {children && <div className={cn(title && "mt-1", "text-ink-muted")}>{children}</div>}
    </div>
  );
}
