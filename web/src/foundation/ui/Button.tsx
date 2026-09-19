import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/foundation/ui/cn";
import { buttonClassName, type ButtonSize, type ButtonVariant } from "@/foundation/ui/buttonStyles";

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
      className={cn(buttonClassName(variant, size), className)}
      {...rest}
    />
  );
});
