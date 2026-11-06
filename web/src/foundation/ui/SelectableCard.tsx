import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";

/** One option in a radio group, drawn as a card. The caller owns the group's role and label. */
export function SelectableCard({
  selected,
  onSelect,
  children,
}: {
  selected: boolean;
  onSelect: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "flex h-full flex-col gap-2 rounded-osce-lg border p-5 text-left transition-colors focus-visible:ring-assess-focus-ring",
        selected
          ? "border-assess-select-border bg-osce-accent-subtle"
          : "border-osce-border bg-osce-surface hover:border-assess-select-border",
      )}
    >
      {children}
    </button>
  );
}
