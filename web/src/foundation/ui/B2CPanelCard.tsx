import type { CSSProperties, ReactNode } from "react";
import type { IconType } from "react-icons";
import { cn } from "@/foundation/ui/cn";
import { cardScrollBody } from "@/foundation/ui/Card";
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
        "flex items-center gap-2.5 px-4 pb-1 pt-[18px] sm:px-5",
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
    <div className={cn("space-y-4 px-4 pb-5 pt-3 sm:px-5", cardScrollBody, className)}>{children}</div>
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
        "flex flex-row flex-wrap items-center justify-end gap-2 bg-osce-surface px-4 pb-5 pt-2 sm:px-5",
        className,
      )}
    >
      {children}
    </div>
  );
}
