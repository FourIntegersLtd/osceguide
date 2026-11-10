import Link from "next/link";
import type { ButtonHTMLAttributes, ComponentProps } from "react";
import { cn } from "@/foundation/ui/cn";

type SiteButtonVariant = "brand" | "line" | "white" | "ghost" | "text";
type SiteButtonSize = "sm" | "md" | "lg";

const VARIANT: Record<SiteButtonVariant, string> = {
  brand: "bg-site-brand text-site-on-brand hover:bg-site-brand-hover border border-transparent",
  line: "bg-transparent text-site-ink border border-site-rule hover:border-site-brand hover:text-site-brand",
  white: "bg-white text-site-deep border border-transparent hover:bg-site-pale",
  ghost: "bg-transparent text-white border border-white/55 hover:border-white",
  text: "bg-transparent text-site-body border border-transparent hover:text-site-brand hover:underline underline-offset-4",
};
const SIZE: Record<SiteButtonSize, string> = {
  sm: "h-11 px-4 text-sm min-[960px]:h-9",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-7 text-base",
};

/** Class string for the public site's pill buttons; use it on anything that must look like one. */
function siteButtonClass(variant: SiteButtonVariant = "brand", size: SiteButtonSize = "md", className?: string): string {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-full font-landing-body font-semibold transition-colors",
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-site-brand",
    "disabled:cursor-not-allowed disabled:opacity-60",
    VARIANT[variant],
    SIZE[size],
    className,
  );
}

type Style = { variant?: SiteButtonVariant; size?: SiteButtonSize };

export function SiteButton({ variant, size, className, type = "button", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & Style) {
  return <button type={type} className={siteButtonClass(variant, size, className)} {...props} />;
}

export function SiteButtonLink({ variant, size, className, ...props }: ComponentProps<typeof Link> & Style) {
  return <Link className={siteButtonClass(variant, size, className)} {...props} />;
}
