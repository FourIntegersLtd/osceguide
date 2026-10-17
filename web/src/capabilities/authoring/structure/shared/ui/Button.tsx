import React from "react";
import { Spinner } from "@/foundation/ui";
import { getButtonClassName } from "./buttonStyles";
import type { ButtonSize, ButtonStyleProps, ButtonVariant } from "./buttonStyles";

export { getButtonClassName };
export type { ButtonSize, ButtonStyleProps, ButtonVariant };

export interface ButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onClick">,
    ButtonStyleProps {
  isLoading?: boolean;
  /** Return the promise and the button shows its spinner until it settles. */
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => unknown;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      fullWidth = false,
      themeType = "b2c",
      children,
      disabled,
      type = "button",
      onClick,
      ...props
    },
    ref,
  ) => {
    const [pending, setPending] = React.useState(false);
    const loading = isLoading || pending;
    const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      const result = onClick?.(event);
      if (result instanceof Promise) {
        setPending(true);
        void result.finally(() => setPending(false));
      }
    };
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        onClick={onClick ? handleClick : undefined}
        className={getButtonClassName({
          variant,
          size,
          fullWidth,
          themeType,
          className,
        })}
        {...props}
      >
        {loading && (
          <Spinner size="sm" className="mr-2 text-current" />
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
