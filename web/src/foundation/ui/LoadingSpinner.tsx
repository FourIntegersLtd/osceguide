import { HiOutlineArrowPath } from "react-icons/hi2";
import { cn } from "@/foundation/ui/cn";

type LoadingSpinnerProps = {
  label?: string;
  /** Show the label beside the spinner as well as announcing it. */
  showLabel?: boolean;
  className?: string;
  size?: "sm" | "md";
};

const LoadingSpinner = ({
  label = "Loading",
  showLabel = false,
  className = "",
  size = "md",
}: LoadingSpinnerProps) => (
  <div
    role="status"
    aria-live="polite"
    className={cn(
      "flex items-center justify-center",
      size === "md" ? "min-h-[200px]" : "h-auto py-4",
      className,
    )}
  >
    <HiOutlineArrowPath
      className={cn(
        "animate-spin text-osce-accent",
        size === "md" ? "h-8 w-8" : "h-4 w-4",
      )}
      aria-hidden
    />
    {showLabel ? (
      <p className="ml-2 text-osce-body text-osce-ink-500">{label}</p>
    ) : null}
    <span className="sr-only">{label}</span>
  </div>
);

export default LoadingSpinner;
