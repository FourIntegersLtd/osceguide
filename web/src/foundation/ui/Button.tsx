import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/foundation/ui/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-ink-inverse hover:bg-accent-hover disabled:bg-ink-subtle",
  secondary:
    "bg-surface text-ink border border-border-strong hover:bg-surface-raised disabled:text-ink-subtle",
  ghost: "text-ink-muted hover:bg-surface-raised hover:text-ink",
  danger: "bg-danger text-ink-inverse hover:brightness-90",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

/**
 * The one button.
 *
 * It carries no surface prop: the accent comes from the custom properties the
 * surface shell set, so this renders correctly on Train, Assess, Hire and the
 * staff console without knowing which it is in.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", className, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-control font-medium",
        "transition-colors disabled:cursor-not-allowed disabled:opacity-70",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    />
  );
});
