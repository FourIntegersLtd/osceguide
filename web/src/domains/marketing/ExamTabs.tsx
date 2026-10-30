"use client";

import { EXAM_CONFIGS, type ExamName } from "./pricingContent";

/** The exam toggle above the price cards; an exam with no plans yet says so. */
export function ExamTabs({
  selected,
  onSelect,
}: {
  selected: ExamName;
  onSelect: (examName: ExamName) => void;
}) {
  return (
      <div className="mb-8 flex justify-center">
        <div className="inline-flex max-w-full flex-wrap justify-center gap-1 rounded-[var(--landing-radius-cta,0.5rem)] border border-landing-warm bg-[color:var(--landing-card-accent,var(--b2c-surface-muted))] p-1">
          {(Object.keys(EXAM_CONFIGS) as ExamName[]).map((examName) => {
            const examData = EXAM_CONFIGS[examName];
            const hasPlans = "plans" in examData && !!examData.plans;
            const isActive = selected === examName;

            return (
              <button
                key={examName}
                type="button"
                onClick={() => onSelect(examName)}
                className={`min-h-11 whitespace-nowrap rounded-[var(--landing-radius-cta,0.375rem)] px-4 py-2 font-landing-body text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas ${
                  isActive
                    ? "border border-landing-warm bg-landing-card text-osce-ink-900 shadow-landing-card"
                    : "border border-transparent text-b2c-text-secondary hover:text-osce-ink-900"
                }`}
              >
                <span className="block">{examData.name}</span>
                {!hasPlans ? (
                  <span className="hidden text-[10px] font-medium uppercase tracking-wide text-[color:var(--landing-badge-soon,#f97316)] lg:block">
                    Coming soon
                  </span>
                ) : (
                  <span className="hidden text-xs text-b2c-text-muted lg:block">
                    {examData.label}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
  );
}
