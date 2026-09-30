import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * Semantic size tokens must not be confused with text colors (and vice
 * versa) — `text-osce-body` is a size, `text-ink` is a color, and
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
            "ink",
            "ink",
            "ink-muted",
            "ink-muted",
            "ink-muted",
            "ink-subtle",
            "ink",
            "ink-muted",
            "ink-subtle",
          ],
        },
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
