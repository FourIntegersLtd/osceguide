import type { ComponentType, ReactNode } from "react";
import { b2cCardPlain } from "@/foundation/ui/productTokens";
import { B2CSectionIconBadge } from "@/foundation/ui/B2CSectionIconBadge";

type B2CEmptyStateProps = {
  icon?: ComponentType<{
    className?: string;
    "aria-hidden"?: boolean | "true" | "false";
  }>;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
};

export function B2CEmptyState({
  icon: Icon,
  title,
  description,
  action,
  className = "",
}: B2CEmptyStateProps) {
  return (
    <div
      className={[
        b2cCardPlain,
        "flex flex-col items-center justify-center gap-3 px-6 py-16 text-center",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {Icon ? (
        <B2CSectionIconBadge tone="primary" size="lg">
          <Icon aria-hidden="true" />
        </B2CSectionIconBadge>
      ) : null}
      <h3 className="text-osce-body font-semibold text-osce-ink-900">
        {title}
      </h3>
      {description ? (
        <p className="max-w-md text-osce-meta text-b2c-text-muted">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
