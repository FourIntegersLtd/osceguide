import type { ReactNode } from "react";
import { B2CMonoEyebrow, B2CSectionIconBadge, cn, productTokens } from "@/foundation/ui";

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

export function DashboardHeader({
  title,
  subtitle,
  eyebrow,
  actions,
}: {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:mb-6 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? <B2CMonoEyebrow className="mb-2 block">{eyebrow}</B2CMonoEyebrow> : null}
        <h1 className={productTokens.b2cDashboardTitle}>{title}</h1>
        {subtitle ? (
          <p className={`mt-1.5 max-w-2xl ${productTokens.b2cBodyText}`}>{subtitle}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}

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
    <section className={cn("mb-6 last:mb-0 sm:mb-8", className)}>
      {title || action ? (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title ? <h2 className={productTokens.b2cSectionTitle}>{title}</h2> : <span />}
          {action}
        </div>
      ) : null}
      {children}
    </section>
  );
}

/** Wide chart on the left, narrow one on the right. */
export function DashboardChartGrid({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-12", className)}>
      {children}
    </div>
  );
}

export function DashboardChartWide({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("min-w-0 lg:col-span-7", className)}>{children}</div>;
}

export function DashboardChartSide({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("min-w-0 lg:col-span-5", className)}>{children}</div>;
}

export function DashboardStatCard({
  title,
  value,
  description,
  icon,
  variant = "default",
  className,
}: {
  title: string;
  value: string | number;
  description?: string;
  icon?: ReactNode;
  variant?: "primary" | "default";
  className?: string;
}) {
  const isPrimary = variant === "primary";

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-osce-lg transition-all",
        productTokens.b2cCardPadding,
        isPrimary
          ? "border border-osce-accent bg-osce-accent text-white"
          : productTokens.b2cDashboardCard,
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p
            className={cn(
              productTokens.b2cMonoEyebrow,
              isPrimary ? "text-white/80" : "text-b2c-text-muted",
            )}
          >
            {title}
          </p>
          <p
            className={cn(
              "mt-3",
              productTokens.b2cStatValue,
              isPrimary ? "text-white" : "text-osce-ink-900",
            )}
          >
            {value}
          </p>
          {description ? (
            <p
              className={cn(
                "mt-2 text-osce-meta leading-relaxed",
                isPrimary ? "text-white/75" : "text-b2c-text-secondary",
              )}
            >
              {description}
            </p>
          ) : null}
        </div>
        {icon ? (
          isPrimary ? (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/15 text-white [&>svg]:h-4 [&>svg]:w-4">
              {icon}
            </div>
          ) : (
            <B2CSectionIconBadge tone="sky" size="md">
              {icon}
            </B2CSectionIconBadge>
          )
        ) : null}
      </div>
    </div>
  );
}

/** The old screens' "No data available" block, kept word for word. */
export function NoDataMessage() {
  return (
    <div className="flex h-[300px] flex-col items-center justify-center text-b2c-text-muted">
      <p className="text-osce-body font-medium">No data available</p>
      <p className="text-osce-body">
        Complete more stations to see your performance distribution
      </p>
    </div>
  );
}
