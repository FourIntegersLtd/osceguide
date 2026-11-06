/*
 * Class-name merging, with the product's own scale taught to tailwind-merge.
 *
 * Brought across from the retiring client rather than kept as the two-line
 * version this project started with, because that one gets `text-osce-body`
 * wrong: it is a *size* token and `text-osce-ink-900` is a *colour* token, and
 * tailwind-merge drops one for the other unless it is told they are different
 * groups.
 */
import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

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
        "text-assess-h1",
        "text-assess-h2",
        "text-assess-desc",
        "text-assess-meta",
        "text-assess-label",
        "text-assess-chip",
        "text-assess-eyebrow",
        "text-assess-num",
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
