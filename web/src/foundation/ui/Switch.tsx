import { cn } from "@/foundation/ui/cn";

/** The canvas switch: 40 by 24, accent when on. */
export function Switch({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  /** What the switch turns on, for a screen reader; the row's title is beside it for everyone else. */
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-6 w-10 shrink-0 rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/30 disabled:opacity-60",
        checked ? "bg-accent" : "bg-border",
      )}
    >
      <span
        className={cn(
          "absolute left-[3px] top-[3px] h-[18px] w-[18px] rounded-full bg-surface shadow-sm transition-transform",
          checked && "translate-x-4",
        )}
        aria-hidden
      />
    </button>
  );
}
