"use client";

import type { ComponentType, ReactNode } from "react";
import { cn } from "@/foundation/ui";
import {
  landingIconPalette,
  type LandingIconColor,
} from "./landingIconPalette";

type LandingIconBadgeProps = {
  icon: ComponentType<{ className?: string }>;
  color: LandingIconColor;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const SIZE_CLASS = {
  sm: {
    shell: "h-9 w-9 rounded-osce-lg",
    icon: "h-4 w-4 stroke-[1.75]",
  },
  md: {
    shell: "h-11 w-11 rounded-[12px]",
    icon: "h-5 w-5 stroke-[1.8]",
  },
  lg: {
    shell: "h-12 w-12 rounded-[14px]",
    icon: "h-5 w-5 stroke-[1.8] sm:h-6 sm:w-6",
  },
} as const;

export function LandingIconBadge({
  icon: Icon,
  color,
  size = "md",
  className,
}: LandingIconBadgeProps) {
  const sizes = SIZE_CLASS[size];

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center text-white",
        sizes.shell,
        className,
      )}
      style={{ backgroundColor: landingIconPalette[color] }}
      aria-hidden
    >
      <Icon className={sizes.icon} />
    </div>
  );
}

type LandingGlyphBadgeProps = {
  children: ReactNode;
  color: LandingIconColor;
  size?: "sm" | "md";
  className?: string;
};

const GLYPH_SIZE = {
  sm: "h-[22px] w-[22px] text-[11px]",
  md: "h-7 w-7 text-xs",
} as const;

export function LandingGlyphBadge({
  children,
  color,
  size = "sm",
  className,
}: LandingGlyphBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-medium text-white",
        GLYPH_SIZE[size],
        className,
      )}
      style={{ backgroundColor: landingIconPalette[color] }}
      aria-hidden
    >
      {children}
    </span>
  );
}
