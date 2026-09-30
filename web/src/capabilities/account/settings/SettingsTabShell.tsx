import type { ReactNode } from "react";
import { ModalContent, cn } from "@/foundation/ui";

/**
 * The column every settings tab sits in.
 *
 * Three fifths on a wide screen, full width for the grids (referrals, the
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
    <ModalContent
      className={cn("w-full space-y-4", fullWidth ? "lg:w-full" : "lg:w-3/5", className)}
    >
      {children}
    </ModalContent>
  );
}
