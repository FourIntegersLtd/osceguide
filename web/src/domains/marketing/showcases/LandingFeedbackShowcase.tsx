"use client";

import { B2CBandPill } from "@/foundation/ui/BandPill";
import {
  FEEDBACK_SHOWCASE_CONTENT,
  type ExamShowcaseVariant,
} from "./examShowcaseContent";

function ReportEyebrow({ children }: { children: string }) {
  return (
    <div className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
      {children}
    </div>
  );
}

type LandingFeedbackShowcaseProps = {
  variant: Extract<ExamShowcaseVariant, "sca" | "plab">;
};

export function LandingFeedbackShowcase({ variant }: LandingFeedbackShowcaseProps) {
  const content = FEEDBACK_SHOWCASE_CONTENT[variant];

  return (
    <div className="overflow-hidden rounded-[var(--landing-radius-panel,10px)] border border-landing-warm bg-landing-card text-left shadow-landing-panel">
      <div className="border-b border-b2c-border-light px-5 py-4 sm:px-6 sm:py-5">
        <ReportEyebrow>Station</ReportEyebrow>
        <div className="mt-3 flex items-center gap-3.5">
          <div className="h-9 w-9 shrink-0 rounded-full bg-gradient-to-br from-osce-accent to-osce-accent-hover sm:h-10 sm:w-10" />
          <div className="min-w-0">
            <div className="font-landing-heading text-lg font-semibold leading-tight tracking-[-0.025em] text-osce-ink-900">
              {content.stationTitle}
            </div>
            <p className="mt-1 font-landing-body text-sm text-b2c-text-secondary">
              {content.patientSummary}
            </p>
          </div>
        </div>
        <p className="mt-3 font-landing-body text-sm text-b2c-text-muted">
          {content.examMeta}
        </p>
      </div>

      <div className="px-5 py-4 sm:px-6 sm:py-5">
        <div className="hidden items-baseline gap-4 border-b border-transparent pb-2.5 sm:flex">
          <div className="flex-1 font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
            Domain
          </div>
          <div className="w-[74px] shrink-0 text-right font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
            Marks
          </div>
          <div className="w-[168px] shrink-0 text-right font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
            Band
          </div>
        </div>

        <div className="divide-y divide-b2c-border-light">
          {content.domains.map((row) => (
            <div
              key={row.domain}
              className="flex flex-col gap-1.5 py-3 sm:flex-row sm:items-baseline sm:gap-4 sm:py-4"
            >
              <div className="min-w-0 flex-1 font-landing-body text-sm font-medium text-osce-ink-900 sm:text-base">
                {row.domain}
              </div>
              <div className="flex items-center justify-between gap-2 sm:contents">
                <div className="font-landing-mono text-sm text-landing-ink-body sm:w-[74px] sm:shrink-0 sm:text-right">
                  {row.marks}
                </div>
                <div className="sm:w-[168px] sm:shrink-0 sm:text-right">
                  <B2CBandPill variant={row.variant} />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-baseline justify-between gap-4 border-t border-b2c-border pt-4">
          <span className="font-landing-body text-sm text-b2c-text-secondary sm:text-base">
            Total
          </span>
          <span className="font-landing-heading text-xl font-semibold tracking-[-0.03em] text-osce-ink-900 sm:text-2xl">
            {content.total}
          </span>
        </div>
      </div>
    </div>
  );
}
