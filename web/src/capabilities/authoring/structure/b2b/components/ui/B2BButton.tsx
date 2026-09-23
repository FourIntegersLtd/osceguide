"use client";
import React from "react";
import { Button } from "@/capabilities/authoring/structure/shared/ui/Button";
import type { ButtonProps } from "@/capabilities/authoring/structure/shared/ui/Button";
type B2BButtonVariant =
  | "primary"
  | "commit"
  | "secondary"
  | "ghost"
  | "danger";
type B2BButtonSize = "md" | "sm" | "xs" | "hero";
function resolveVariant(
  variant: B2BButtonVariant,
  size: B2BButtonSize,
): ButtonProps["variant"] {
  if (variant === "danger" && (size === "md" || size === "hero")) {
    return "dangerSolid";
  }
  if (variant === "danger") {
    return "danger";
  }
  return variant;
}
export function B2BButton({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  children,
  ...rest
}: Omit<ButtonProps, "themeType" | "variant" | "size"> & {
  variant?: B2BButtonVariant;
  size?: B2BButtonSize;
}) {
  return (
    <Button
      themeType="b2b"
      variant={resolveVariant(variant, size)}
      size={size}
      type={type}
      className={className}
      {...rest}
    >
      {" "}
      {children}{" "}
    </Button>
  );
}
