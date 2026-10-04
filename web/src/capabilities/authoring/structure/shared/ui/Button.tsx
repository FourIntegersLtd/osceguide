import React from "react";
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
          <svg
            className="mr-2 h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
