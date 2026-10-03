import type { ReactNode } from "react";
import { cn } from "@/foundation/ui";

/**
 * The column every settings tab sits in.
 *
 * A reading column of cards, full width for the grids (referrals, the
 * tutor's memory). The retiring version also widened itself when the help
 * drawer opened, by reading a consumer-only context; a capability cannot see
 * that, and the tab says what it needs instead.
 */
export function SettingsTabShell({
  children,
  className = "",
  fullWidth = false,
}: {
  children: ReactNode;
  className?: string;
  fullWidth?: boolean;
}) {
  return (
    <div className={cn("w-full space-y-6", fullWidth ? "" : "max-w-[960px]", className)}>{children}</div>
  );
}
