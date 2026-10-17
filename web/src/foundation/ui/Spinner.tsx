import { HiOutlineArrowPath } from "react-icons/hi2";
import { cn } from "@/foundation/ui/cn";

const SIZE = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" } as const;

/** The one spinner: the ClinicalBuddy arrow, drawn in the surrounding text colour. */
export function Spinner({
  label = "Loading",
  size = "sm",
  className,
}: {
  label?: string;
  /** `sm` for inline and button use, `md` for a panel, `lg` for a page or shell. */
  size?: keyof typeof SIZE;
  /** Sets the colour through `text-*`; defaults to the surrounding text. */
  className?: string;
}) {
  return (
    <span role="status" aria-label={label} className="inline-flex">
      <HiOutlineArrowPath className={cn("animate-spin", SIZE[size], className)} aria-hidden />
    </span>
  );
}
