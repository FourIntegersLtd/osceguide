import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * Semantic size tokens must not be confused with text colors (and vice
 * versa) — `text-osce-body` is a size, `text-osce-ink-900` is a color, and
 * tailwind-merge cannot tell them apart without being told.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        "text-osce-caption",
        "text-osce-meta",
        "text-osce-data",
        "text-osce-body",
        "text-osce-subheading",
        "text-osce-title",
        "text-osce-heading",
        "text-osce-display-sm",
        "text-osce-display",
        "text-osce-display-lg",
      ],
      "text-color": [
        {
          text: [
            "osce-ink-900",
            "osce-ink-800",
            "osce-ink-700",
            "osce-ink-600",
            "osce-ink-500",
            "osce-ink-400",
            "b2c-text-primary",
            "b2c-text-secondary",
            "b2c-text-muted",
          ],
        },
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
