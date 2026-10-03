import { cn } from "@/foundation/ui/cn";

/**
 * The canvas's 8px competency bar: competent, developing and development
 * side by side, each as wide as its share. Shares are percentages.
 */
export function B2CBandBar({
  competent,
  developing,
  development,
  className,
}: {
  competent: number;
  developing: number;
  development: number;
  className?: string;
}) {
  const total = competent + developing + development;
  const share = (value: number) => (total > 0 ? `${(value / total) * 100}%` : "0%");
  return (
    <div
      className={cn("flex h-2 gap-0.5 overflow-hidden rounded-full bg-b2c-surface-muted", className)}
      role="img"
      aria-label={`${competent}% competent, ${developing}% developing, ${development}% development`}
    >
      {competent > 0 ? <span className="bg-osce-band-competentBar" style={{ width: share(competent) }} /> : null}
      {developing > 0 ? <span className="bg-osce-band-developingBar" style={{ width: share(developing) }} /> : null}
      {development > 0 ? <span className="bg-osce-band-developmentBar" style={{ width: share(development) }} /> : null}
    </div>
  );
}
