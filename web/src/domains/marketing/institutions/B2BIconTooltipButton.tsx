"use client";

import type { ButtonHTMLAttributes, MouseEvent, ReactNode } from "react";
import { B2BIconTooltipShell } from "@/domains/marketing/institutions/B2BIconTooltipShell";
import {
  b2bIconButtonGhost,
  b2bIconButtonPrimarySm,
  b2bIconButtonSm,
  type B2BIconTooltipPlacement,
} from "@/foundation/ui/b2bTokens";

function variantClass(
  variant: "default" | "primary" | "danger" | "warning" | "ghost",
): string {
  switch (variant) {
    case "primary":
      return b2bIconButtonPrimarySm;
    case "danger":
      return `${b2bIconButtonSm} text-b2b-danger-text hover:bg-b2b-danger-bg`;
    case "warning":
      return `${b2bIconButtonSm} text-b2b-warning-text hover:bg-b2b-warning-bg`;
    case "ghost":
      return b2bIconButtonGhost;
    case "default":
    default:
      return b2bIconButtonSm;
  }
}

type Props = {
  label: string;
  /**
   * Set false for controls whose icon is self-explanatory (close, dismiss,
   * undo). The accessible name is kept via `aria-label`; only the hover chip
   * is suppressed.
   */
  showTooltip?: boolean;
  disabled?: boolean;
  onClick?: (event: MouseEvent<HTMLButtonElement>) => void | Promise<void>;
  children: ReactNode;
  tooltipPlacement?: B2BIconTooltipPlacement;
  variant?: "default" | "primary" | "danger" | "warning" | "ghost";
  buttonClassName?: string;
} & Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "children" | "onClick" | "disabled" | "className" | "type" | "aria-label" | "title"
>;

/** Icon-only control with a designed hover/focus tooltip chip. */
export function B2BIconTooltipButton({
  label,
  showTooltip = true,
  disabled,
  onClick,
  children,
  tooltipPlacement = "bottom",
  variant = "default",
  buttonClassName,
  ...buttonProps
}: Props) {
  const classes = [variantClass(variant), buttonClassName]
    .filter(Boolean)
    .join(" ");

  const button = (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className={classes}
      {...buttonProps}
    >
      {children}
    </button>
  );

  if (!showTooltip) return button;

  return (
    <B2BIconTooltipShell label={label} placement={tooltipPlacement}>
      {button}
    </B2BIconTooltipShell>
  );
}
