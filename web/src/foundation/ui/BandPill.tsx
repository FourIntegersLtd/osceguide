import { cn } from "@/foundation/ui/cn";
import {
  b2cBandPillCompetent,
  b2cBandPillDeveloping,
  b2cBandPillDevelopment,
} from "@/foundation/ui/productTokens";

export type B2CBandVariant = "competent" | "developing" | "development";

const variantClasses: Record<B2CBandVariant, string> = {
  competent: b2cBandPillCompetent,
  developing: b2cBandPillDeveloping,
  development: b2cBandPillDevelopment,
};

const labels: Record<B2CBandVariant, string> = {
  competent: "Competent",
  developing: "Developing",
  development: "Needs Development",
};

const compactLabels: Record<B2CBandVariant, string> = {
  competent: "Comp",
  developing: "Devlpg",
  development: "Needs Devt",
};

type B2CBandPillProps = {
  variant: B2CBandVariant;
  label?: string;
  compact?: boolean;
  className?: string;
};

export function B2CBandPill({
  variant,
  label,
  compact = false,
  className,
}: B2CBandPillProps) {
  const displayLabel =
    label ?? (compact ? compactLabels[variant] : labels[variant]);

  return (
    <span className={cn(variantClasses[variant], "whitespace-nowrap", className)}>
      {displayLabel}
    </span>
  );
}
