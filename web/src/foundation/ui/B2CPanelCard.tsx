import type { CSSProperties, ReactNode } from "react";
import type { IconType } from "react-icons";
import { cn } from "@/foundation/ui/cn";
import { b2cCard, b2cPanelCardHeader } from "@/foundation/ui/productTokens";
import {
  B2CSectionIconBadge,
  type B2CSectionIconTone,
} from "@/foundation/ui/B2CSectionIconBadge";

/**
 * Section card aligned to marketplace AvailabilityPostCard:
 * shell = b2cCard, header = border-b + bg-b2c-surface-muted.
 */

export function B2CPanelCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(b2cCard, "mt-4 min-w-0 max-w-full overflow-hidden", className)}
    >
      {children}
    </div>
  );
}

/** Same classes as AvailabilityPostCard header band. */
export function B2CPanelCardHeaderIcon({
  icon: Icon,
  tone = "primary",
}: {
  icon: IconType;
  tone?: B2CSectionIconTone;
}) {
  return (
    <B2CSectionIconBadge tone={tone}>
      <Icon aria-hidden />
    </B2CSectionIconBadge>
  );
}

export function B2CPanelCardHeader({
  children,
  className = "",
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 border-b border-b2c-border bg-b2c-surface-muted px-4 py-3",
        b2cPanelCardHeader,
        className,
      )}
      style={style}
    >
      {children}
    </div>
  );
}

export function B2CPanelCardBody({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-4 p-3 sm:p-4", className)}>{children}</div>
  );
}

/** Actions sit bottom-right on the white card surface (no divider above buttons). */
export function B2CPanelCardFooter({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-row flex-wrap items-center justify-end gap-x-2 gap-y-3 bg-osce-surface px-4 pb-3 pt-6 sm:gap-y-2",
        className,
      )}
    >
      {children}
    </div>
  );
}
