"use client";

import {
  MANAGEMENT_SHOWCASE_CONTENT,
  type ExamShowcaseVariant,
} from "./examShowcaseContent";

type LandingManagementShowcaseProps = {
  variant: Extract<ExamShowcaseVariant, "sca" | "plab">;
};

export function LandingManagementShowcase({
  variant,
}: LandingManagementShowcaseProps) {
  const content = MANAGEMENT_SHOWCASE_CONTENT[variant];

  return (
    <div className="overflow-hidden rounded-[var(--landing-radius-panel,10px)] border border-landing-warm bg-landing-card shadow-landing-panel">
      <div className="border-b border-b2c-border-light bg-[linear-gradient(180deg,#FCFCFD_0%,#FFFFFF_100%)] px-5 py-4 sm:px-6 sm:py-5">
        <div className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-b2c-text-muted">
          Management plan
        </div>
        <h3 className="mt-1.5 font-landing-heading text-lg font-semibold tracking-[-0.02em] text-osce-ink-900 sm:text-xl">
          {content.title}
        </h3>
        <p className="mt-1 font-landing-body text-sm text-b2c-text-secondary">
          {content.subtitle}
        </p>
      </div>

      <div className="divide-y divide-b2c-border-light">
        {content.sections.map((section) => (
          <div key={section.heading} className="px-5 py-4 sm:px-6 sm:py-5">
            <h4 className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-b2c-text-muted">
              {section.heading}
            </h4>
            <ul className="mt-3 space-y-2">
              {section.items.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-2.5 font-landing-body text-sm leading-relaxed text-landing-ink-body"
                >
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-osce-accent" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
