import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";

export function EmptyState({
  title,
  description,
  action,
  bare = false,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  /**
   * No dashed outline, for an empty state that sits inside a panel's own
   * full-bleed body — an outlined box inside an outlined panel reads as a box
   * in a box.
   */
  bare?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 px-6 py-10 text-center",
        bare ? "" : "rounded-osce-lg border border-dashed border-border",
      )}
    >
      <p className="text-osce-data font-semibold text-ink">{title}</p>
      {description && (
        <p className="max-w-sm text-osce-meta text-ink-subtle">{description}</p>
      )}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
