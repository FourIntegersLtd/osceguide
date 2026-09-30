"use client";

import type { ReactNode } from "react";
import { AnchoredTooltip } from "@/foundation/ui/AnchoredTooltip";
import {
  b2bIconTooltipChipBase,
  type B2BIconTooltipPlacement,
} from "@/foundation/ui/b2bTokens";

type B2BIconTooltipShellProps = {
  label: string;
  placement?: B2BIconTooltipPlacement;
  children: ReactNode;
  className?: string;
};

/**
 * Hover/focus tooltip chip wrapper for icon-only buttons and links. The chip is
 * portalled to the body so scrolling ancestors (collapsed sidebar, tables,
 * toasts) cannot clip it.
 */
export function B2BIconTooltipShell({
  label,
  placement = "bottom",
  children,
  className = "",
}: B2BIconTooltipShellProps) {
  return (
    <AnchoredTooltip
      label={label}
      placement={placement}
      chipClassName={b2bIconTooltipChipBase}
      className={className}
    >
      {children}
    </AnchoredTooltip>
  );
}
