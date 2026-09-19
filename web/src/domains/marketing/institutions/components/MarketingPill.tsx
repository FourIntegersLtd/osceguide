import type { ReactNode } from "react";

type MarketingPillProps = {
  children: ReactNode;
};

export function MarketingPill({ children }: MarketingPillProps) {
  return (
    <div className="inline-flex items-center rounded-full border border-landing-warm bg-landing-card px-3.5 py-1.5 font-landing-body text-xs font-medium text-landing-ink-body shadow-landing-card">
      {children}
    </div>
  );
}
