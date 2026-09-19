import Link from "next/link";
import type { ComponentProps } from "react";
import { cn } from "@/foundation/ui/cn";

export interface TextLinkProps extends ComponentProps<typeof Link> {
  variant?: "primary" | "muted";
  themeType?: "b2c" | "b2b";
}

export function TextLink({
  variant = "primary",
  themeType = "b2c",
  className,
  ...props
}: TextLinkProps) {
  const styles =
    themeType === "b2b"
      ? variant === "muted"
        ? "font-medium text-b2b-accent hover:text-b2b-accent-hover"
        : "font-semibold text-b2b-accent hover:text-b2b-accent-hover"
      : variant === "muted"
        ? "font-medium text-osce-accent hover:text-osce-accent-hover"
        : "font-semibold text-osce-accent hover:text-osce-accent-hover";

  return <Link className={cn(styles, className)} {...props} />;
}
