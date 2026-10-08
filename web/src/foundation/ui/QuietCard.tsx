import type { ReactNode } from "react";
import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader } from "@/foundation/ui/B2CPanelCard";

/**
 * The opened item on a quiet-kit screen: a title and muted subtitle over a
 * body, with the screen's actions at the foot (one primary, the rest ghost).
 */
export function QuietCard({
  title,
  subtitle,
  actions,
  children,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader className="flex-col items-start gap-0.5">
        <h2 className="text-osce-data font-semibold text-ink">{title}</h2>
        {subtitle ? <p className="text-osce-meta text-ink-muted">{subtitle}</p> : null}
      </B2CPanelCardHeader>
      <B2CPanelCardBody>
        {children}
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}
