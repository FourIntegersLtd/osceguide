import type { ReactNode } from "react";
import { B2CSectionIconBadge, cn, productTokens } from "@/foundation/ui";

/**
 * The dashboard's own furniture, brought across from
 * `b2c/components/shared/dashboard` with the screen that uses it.
 *
 * It stays here rather than in `foundation/ui` because only this screen has
 * ever used it: an asymmetric chart grid and a stat card shaped around a
 * percentage are a dashboard's layout, not the product's vocabulary. If the
 * institution dashboard (J13) wants the same grid, that is the moment to move
 * it down a tier.
 */

export function DashboardSection({
  title,
  action,
  children,
  className,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("mb-6 last:mb-0", className)}>
      {title || action ? (
        <div className="mb-2 flex items-center justify-between gap-3 px-1">
          {title ? <h2 className={productTokens.b2cMonoEyebrow}>{title}</h2> : <span />}
          {action}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function DashboardStatCard({
  title,
  value,
  description,
  icon,
  className,
}: {
  title: string;
  value: string | number;
  description?: string;
  icon?: ReactNode;
  /** Kept for callers; cards are quiet, so a "primary" stat looks like the rest. */
  variant?: "primary" | "default";
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-osce-lg transition-all",
        productTokens.b2cCardPadding,
        productTokens.b2cCard,
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p
            className={cn(
              productTokens.b2cMonoEyebrow,
              "text-b2c-text-muted",
            )}
          >
            {title}
          </p>
          <p
            className={cn(
              "mt-3",
              productTokens.b2cStatValue,
              "text-osce-ink-900",
            )}
          >
            {value}
          </p>
          {description ? (
            <p
              className={cn(
                "mt-2 text-osce-meta leading-relaxed",
                "text-b2c-text-muted",
              )}
            >
              {description}
            </p>
          ) : null}
        </div>
        {icon ? (
          <B2CSectionIconBadge tone="sky" size="md">
            {icon}
          </B2CSectionIconBadge>
        ) : null}
      </div>
    </div>
  );
}

/** The old screens' "No data available" block, kept word for word. */
export function NoDataMessage() {
  return (
    <div className="flex h-[220px] flex-col items-center justify-center text-center">
      <p className="font-medium text-osce-ink-900">No data available</p>
      <p className="mt-1 text-osce-meta text-b2c-text-muted">
        Complete more stations to see your performance distribution
      </p>
    </div>
  );
}
