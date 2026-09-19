import Link from "next/link";
import type { ComponentProps } from "react";
import { cn } from "@/foundation/ui/cn";
import { buttonClassName, type ButtonSize, type ButtonVariant } from "@/foundation/ui/buttonStyles";

export interface ButtonLinkProps extends ComponentProps<typeof Link> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

/**
 * A link that looks like a button.
 *
 * Separate from `Button` rather than a polymorphic `as` prop: a navigation is a
 * link and must stay one for middle-click, open-in-new-tab and the keyboard.
 */
export function ButtonLink({ variant = "primary", size = "md", className, ...rest }: ButtonLinkProps) {
  return <Link className={cn(buttonClassName(variant, size), className)} {...rest} />;
}
