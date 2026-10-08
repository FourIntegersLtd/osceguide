"use client";

import { Button } from "@/foundation/ui";
import type { ExamConfig } from "./pricingContent";
import type { LandingType } from "./landingTypography";

export const POPULAR_BADGE_CLASS =
  "font-landing-mono text-[10px] font-medium uppercase tracking-[0.08em] text-osce-accent-hover bg-osce-accent-muted border border-osce-accent-subtle rounded px-[7px] py-[5px]";


const ALL_FEATURES = [
  "Stations Included",
  "Attempts per Station",
  "Real-Time Speech Transcription",
  "RCGP Aligned Structured Feedback",
  "GMC Aligned Structured Feedback",
  "Performance Analytics (Basic)",
  "In-Depth Performance Analytics",
  "Athena as Doctor",
  "Debrief with Athena",
  "Podcast Feature",
  "A to Z (Primary Care Conditions)",
];


export type PricingTableProps = {
  examConfig: ExamConfig & { plans: NonNullable<ExamConfig["plans"]> };
  onSelectPlan: () => void;
  type: LandingType;
};

export function PricingTable({ examConfig, onSelectPlan }: PricingTableProps) {
  const hasFeature = (planFeatures: readonly string[], featureName: string) =>
    planFeatures.includes(featureName);

  const alignedFeedbackLabel =
    examConfig.name === "SCA"
      ? "RCGP Aligned Structured Feedback"
      : "GMC Aligned Structured Feedback";

  const filteredFeatures = ALL_FEATURES.filter((feature) => {
    let shouldKeep = true;
    if (feature === "RCGP Aligned Structured Feedback" && examConfig.name !== "SCA") {
      shouldKeep = false;
    }
    if (feature === "GMC Aligned Structured Feedback" && examConfig.name !== "PLAB 2") {
      shouldKeep = false;
    }
    if (
      feature === "Performance Analytics (Basic)" &&
      ALL_FEATURES.includes("In-Depth Performance Analytics")
    ) {
      if (
        Object.values(examConfig.plans).some((plan) =>
          plan.features.includes("In-Depth Performance Analytics"),
        )
      ) {
        shouldKeep = false;
      }
    }
    if (
      feature === "In-Depth Performance Analytics" &&
      ALL_FEATURES.includes("Performance Analytics (Basic)")
    ) {
      if (
        Object.values(examConfig.plans).every(
          (plan) =>
            !plan.features.includes("In-Depth Performance Analytics") &&
            plan.features.includes("Performance Analytics (Basic)"),
        )
      ) {
        shouldKeep = false;
      }
    }
    if (feature === "Podcast Feature" && examConfig.name !== "SCA") {
      shouldKeep = false;
    }
    if (feature === "A to Z (Primary Care Conditions)" && examConfig.name !== "SCA") {
      shouldKeep = false;
    }
    return shouldKeep;
  });

  const mappedFeatures = filteredFeatures.map((feature) => {
    if (
      feature === "RCGP Aligned Structured Feedback" ||
      feature === "GMC Aligned Structured Feedback"
    ) {
      return "Feedback";
    }
    if (
      feature === "Performance Analytics (Basic)" ||
      feature === "In-Depth Performance Analytics"
    ) {
      return "Performance Analytics";
    }
    if (feature === "Athena as Doctor") {
      return "Athena (Doctor Role)";
    }
    if (feature === "Debrief with Athena") {
      return "Athena Debrief";
    }
    return feature;
  });

  const relevantFeatures = mappedFeatures.filter(
    (value, index, self) => self.indexOf(value) === index,
  );

  const planEntries = Object.entries(examConfig.plans);

  return (
    <table className="w-full min-w-[720px] border-collapse">
      <thead>
        <tr className="border-b border-landing-warm">
          <th
            className="bg-landing-card-muted px-6 py-5 text-left font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-b2c-text-muted"
          >
            Features
          </th>
          {planEntries.map(([planKey, plan], index, arr) => (
            <th
              key={planKey}
              className={`relative px-6 py-5 text-center ${
                plan.isPopular ? "bg-landing-card-accent" : "bg-landing-card-muted"
              } ${index === arr.length - 1 ? "" : ""}`}
            >
              {plan.isPopular ? (
                <div className="mb-3 flex justify-center">
                  <span className={POPULAR_BADGE_CLASS}>Most chosen</span>
                </div>
              ) : (
                <div className="mb-3 h-[26px]" aria-hidden />
              )}
              <div className="font-landing-heading text-base font-semibold tracking-[-0.02em] text-osce-ink-900">
                {plan.name}
              </div>
              <div
                className={`mt-2 font-landing-mono text-[28px] font-medium leading-none ${
                  plan.isPopular ? "text-landing-price" : "text-osce-ink-900"
                }`}
              >
                {plan.price > 0 ? `£${plan.price.toFixed(2)}` : "Free"}
              </div>
              {plan.originalPrice ? (
                <div className="mt-1 font-landing-body text-xs text-b2c-text-muted line-through">
                  £{plan.originalPrice.toFixed(2)}
                </div>
              ) : null}
              {plan.duration ? (
                <div className="mt-1 font-landing-body text-xs text-b2c-text-secondary">
                  {plan.duration} access
                </div>
              ) : null}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-landing-hairline">
        {relevantFeatures.map((featureName) => (
          <tr key={featureName}>
            <td className="px-6 py-3.5 font-landing-body text-sm font-medium text-osce-ink-900">
              {featureName}
            </td>
            {Object.values(examConfig.plans).map((plan, index) => (
              <td
                key={`${featureName}-${index}`}
                className={`px-6 py-3.5 text-center font-landing-body text-sm text-b2c-text-secondary ${
                  plan.isPopular ? "bg-landing-card-accent" : "bg-landing-card"
                }`}
              >
                {(() => {
                  if (featureName === "Stations Included") {
                    return plan.stations;
                  }
                  if (featureName === "Attempts per Station") {
                    return 3;
                  }
                  if (featureName === "Performance Analytics") {
                    if (plan.features.includes("In-Depth Performance Analytics")) {
                      return "Advanced";
                    }
                    if (plan.features.includes("Performance Analytics (Basic)")) {
                      return "Basic";
                    }
                    return <span className="text-b2c-text-muted">-</span>;
                  }
                  if (featureName === "Feedback") {
                    return hasFeature(plan.features, alignedFeedbackLabel)
                      ? alignedFeedbackLabel
                      : <span className="text-b2c-text-muted">-</span>;
                  }

                  let featureKeyToCheck = featureName;
                  if (featureName === "Athena (Doctor Role)") {
                    featureKeyToCheck = "Athena as Doctor";
                  }
                  if (featureName === "Athena Debrief") {
                    featureKeyToCheck = "Debrief with Athena";
                  }
                  if (featureName === "A-Z") {
                    featureKeyToCheck = "A to Z (Primary Care Conditions)";
                  }

                  return hasFeature(plan.features, featureKeyToCheck)
                    ? <span className="font-landing-mono text-base text-[color:var(--landing-tick,#2CA01C)]">✓</span>
                    : <span className="text-b2c-text-muted">-</span>;
                })()}
              </td>
            ))}
          </tr>
        ))}
        <tr>
          <td className="bg-landing-card-muted px-6 py-5" />
          {Object.values(examConfig.plans).map((plan, index) => (
            <td
              key={`button-${index}`}
              className={`px-6 py-5 text-center ${
                plan.isPopular ? "bg-landing-card-accent" : "bg-landing-card-muted"
              }`}
            >
              <Button
                onClick={onSelectPlan}
                variant={plan.ctaColor === "blue" ? "primary" : "commit"}
                size="md"
                fullWidth
              >
                {plan.cta}
              </Button>
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}
