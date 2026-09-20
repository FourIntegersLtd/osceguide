"use client";

import { platformStaffHairlineB } from "@/domains/platform/platformStaffChrome";

const STEPS = [
  { id: 1 as const, label: "Start" },
  { id: 2 as const, label: "Sections & fields" },
];

/** Wizard steps without the B2B tab-strip hairline. */
export function PlatformTemplateWizardStepStrip({
  step,
  onStepChange,
}: {
  step: 1 | 2;
  onStepChange: (step: 1 | 2) => void;
}) {
  return (
    <div
      className={`flex flex-wrap items-center gap-4 px-5 py-2 sm:px-6 ${platformStaffHairlineB}`}
      role="tablist"
      aria-label="Wizard steps"
    >
      {STEPS.map((s) => {
        const active = step === s.id;
        const enabled = s.id <= step;
        return (
          <button
            key={s.id}
            type="button"
            role="tab"
            disabled={!enabled}
            aria-selected={active}
            onClick={() => {
              if (!enabled) return;
              onStepChange(s.id);
            }}
            className={[
              "inline-flex items-center gap-2 rounded-md px-2 py-1.5 text-osce-body font-medium transition-colors",
              !enabled
                ? "cursor-not-allowed text-b2c-text-muted"
                : active
                  ? "bg-b2c-surface-muted text-osce-ink-900"
                  : "text-b2c-text-muted hover:bg-b2c-surface-muted/80 hover:text-osce-ink-900",
            ].join(" ")}
          >
            <span
              className={[
                "flex h-6 w-6 items-center justify-center rounded-full text-osce-caption font-semibold",
                active ? "bg-osce-accent text-white" : "bg-b2c-surface-muted text-b2c-text-secondary",
              ].join(" ")}
            >
              {s.id}
            </span>
            {s.label}
          </button>
        );
      })}
    </div>
  );
}

import { platformStaffHairlineT } from "@/domains/platform/platformStaffChrome";

export const platformTemplateWizardFooterClass = `flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 ${platformStaffHairlineT}`;

export const platformTemplateWizardFooterEndClass = `flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-end sm:px-6 ${platformStaffHairlineT}`;
