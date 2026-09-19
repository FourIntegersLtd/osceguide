import Link from "next/link";
import type { ComponentProps } from "react";
import { getButtonClassName } from "@/foundation/ui/Button";
import type { ButtonStyleProps } from "@/foundation/ui/Button";

type ButtonLinkProps = ComponentProps<typeof Link> &
  Omit<ButtonStyleProps, "themeType"> & {
    themeType?: ButtonStyleProps["themeType"];
  };

export function ButtonLink({
  variant = "primary",
  size = "md",
  fullWidth = false,
  themeType = "b2c",
  className,
  ...props
}: ButtonLinkProps) {
  return (
    <Link
      className={getButtonClassName({
        themeType,
        variant,
        size,
        fullWidth,
        className,
      })}
      {...props}
    />
  );
}
