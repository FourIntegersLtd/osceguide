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
    bodyMuted: b2c ? "text-ink-subtle" : "text-ink-muted",
    captionMuted: b2c ? "text-ink-subtle" : "text-ink-muted",
    iconMuted: b2c ? "text-ink-subtle" : "text-ink-subtle",
    listBorder: b2c ? "border-border" : "border-border",
    listDivide: b2c ? "divide-border" : "divide-border",
    rowHover: b2c ? "hover:bg-surface-raised/60" : "hover:bg-surface-raised",
    inputBorder: b2c ? "border-border" : "border-border",
    headline: b2c ? "text-ink" : "text-ink",
    accentLink: b2c ? "text-osce-accent hover:underline" : "text-accent hover:underline",
    searchIcon: b2c ? "text-ink-subtle/60" : "text-ink-muted/60",
  };
}
