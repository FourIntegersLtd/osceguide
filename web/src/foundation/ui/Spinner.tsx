import { HiOutlineArrowPath } from "react-icons/hi2";
import { cn } from "./cn";

const SIZE = { xs: "h-3.5 w-3.5", sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" } as const;

/**
 * The one spinner: the ClinicalBuddy arrow. Muted (`text-ink-subtle`) unless `className`
 * sets another `text-*`, which wins through `cn`. Inside a button, pass `text-current`
 * so it takes the button's text colour.
 */
export function Spinner({
  label = "Loading",
  size = "sm",
  className,
}: {
  label?: string;
  /** `xs` for dense buttons, `sm` for inline use, `md` for a panel, `lg` for a page or shell. */
  size?: keyof typeof SIZE;
  className?: string;
}) {
  return (
    <span role="status" aria-label={label} className="inline-flex shrink-0">
      <HiOutlineArrowPath className={cn("animate-spin text-ink-subtle", SIZE[size], className)} aria-hidden />
    </span>
  );
}
