"use client";

import { EXAM_CONFIGS, VISIBLE_EXAMS, type ExamName } from "./pricingContent";

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
        <div className="inline-flex max-w-full flex-wrap justify-center gap-1 rounded-full border border-site-line bg-site-ground p-1">
          {VISIBLE_EXAMS.map((examName) => {
            const examData = EXAM_CONFIGS[examName];
            const hasPlans = "plans" in examData && !!examData.plans;
            const isActive = selected === examName;

            return (
              <button
                key={examName}
                type="button"
                onClick={() => onSelect(examName)}
                className={`min-h-11 whitespace-nowrap rounded-full px-4 py-2 font-landing-body text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-site-brand ${
                  isActive
                    ? "border border-site-line bg-site-card text-site-ink"
                    : "border border-transparent text-site-body hover:text-site-ink"
                }`}
              >
                <span className="block">{examData.name}</span>
                {!hasPlans ? (
                  <span className="hidden text-[10px] font-medium uppercase tracking-wide text-site-amber lg:block">
                    Coming soon
                  </span>
                ) : (
                  <span className="hidden text-xs text-site-muted lg:block">
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
