import { cn } from "@/foundation/ui";

/** The small dot that says a warning cue is active while the cues panel is out of sight. */
export function AlertDot({ className }: { className: string }) {
  return <span role="img" aria-label="Live cues need attention" className={cn("rounded-full bg-osce-warning-icon", className)} />;
}
