import type { ComponentType, ReactNode } from "react";
import {
  b2bChipHueClasses,
  b2bIconChipBase,
  type B2BChipHue,
} from "@/capabilities/authoring/structure/b2b/theme/b2bUi";

type B2BIconChipProps = {
  icon: ComponentType<{
    className?: string;
    "aria-hidden"?: boolean | "true" | "false";
  }>;
  hue?: B2BChipHue;
  /** Smaller chip for dense tables / grouped rows. */
  size?: "sm" | "md";
  className?: string;
  children?: ReactNode;
};

const sizeClasses = {
  sm: "h-8 w-8 [&>svg]:h-4 [&>svg]:w-4",
  md: "h-9 w-9 [&>svg]:h-[18px] [&>svg]:w-[18px]",
} as const;

/** Tinted square icon holder (Notion-settings style). */
export function B2BIconChip({
  icon: Icon,
  hue = "blue",
  size = "md",
  className = "",
  children,
}: B2BIconChipProps) {
  return (
    <span
      className={[
        b2bIconChipBase,
        b2bChipHueClasses[hue],
        sizeClasses[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      aria-hidden={children ? undefined : true}
    >
      {children ?? <Icon className="shrink-0" aria-hidden="true" />}
    </span>
  );
}
