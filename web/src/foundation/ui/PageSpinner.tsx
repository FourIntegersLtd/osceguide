import { cn } from "./cn";
import { Spinner } from "./Spinner";

/**
 * A big spinner centred in the space a page or section will fill:
 * `screen` for a whole page, `section` for a screen inside a shell.
 */
export function PageSpinner({
  label,
  fill = "screen",
  className,
}: {
  label?: string;
  fill?: "screen" | "section";
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-center", fill === "screen" ? "min-h-screen" : "min-h-[40vh]", className)}>
      <Spinner label={label} size="lg" />
    </div>
  );
}
