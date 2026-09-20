"use client";

import { useSurface } from "@/capabilities";
import type { ButtonProps } from "@/foundation/ui/Button";

/**
 * Staff console authoring uses B2C chrome; institution/partner arms keep B2B.
 */
export function useAuthoringChrome() {
  const { surface } = useSurface();
  const b2c = surface === "platform";

  return {
    b2c,
    themeType: b2c ? ("b2c" as const) : ("b2b" as const),
    primaryVariant: (b2c ? "primary" : "commit") as ButtonProps["variant"],
    bodyMuted: b2c ? "text-b2c-text-muted" : "text-b2b-mid",
    captionMuted: b2c ? "text-b2c-text-muted" : "text-b2b-mid",
    iconMuted: b2c ? "text-b2c-text-muted" : "text-b2b-icon",
    listBorder: b2c ? "border-b2c-border" : "border-b2b-border",
    listDivide: b2c ? "divide-b2c-border" : "divide-b2b-border",
    rowHover: b2c ? "hover:bg-b2c-secondary/60" : "hover:bg-b2b-cream",
    inputBorder: b2c ? "border-b2c-border" : "border-b2b-border",
    headline: b2c ? "text-osce-ink-900" : "text-b2b-headline",
    accentLink: b2c ? "text-osce-accent hover:underline" : "text-b2b-accent hover:underline",
    searchIcon: b2c ? "text-b2c-text-muted/60" : "text-b2b-mid/60",
  };
}
