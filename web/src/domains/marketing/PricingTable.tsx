"use client";

import { SiteButton } from "@/foundation/ui";
import type { ExamConfig } from "./pricingContent";

export const POPULAR_BADGE_CLASS =
  "font-landing-mono text-[10px] font-medium uppercase tracking-[0.08em] text-site-brand bg-site-pale border border-site-line rounded px-[7px] py-[5px]";


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
        <tr className="border-b border-site-line">
          <th
            className="bg-site-pale px-6 py-5 text-left font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-site-muted"
          >
            Features
          </th>
          {planEntries.map(([planKey, plan], index, arr) => (
            <th
              key={planKey}
              className={`relative px-6 py-5 text-center ${
                "bg-site-pale"
              } ${index === arr.length - 1 ? "" : ""}`}
            >
              {plan.isPopular ? (
                <div className="mb-3 flex justify-center">
                  <span className={POPULAR_BADGE_CLASS}>Most chosen</span>
                </div>
              ) : (
                <div className="mb-3 h-[26px]" aria-hidden />
              )}
              <div className="font-landing-heading text-base font-semibold tracking-[-0.02em] text-site-ink">
                {plan.name}
              </div>
              <div
                className={`mt-2 font-landing-mono text-[28px] font-medium leading-none ${
                  plan.isPopular ? "text-site-brand" : "text-site-ink"
                }`}
              >
                {plan.price > 0 ? `£${plan.price.toFixed(2)}` : "Free"}
              </div>
              {plan.originalPrice ? (
                <div className="mt-1 font-landing-body text-xs text-site-muted line-through">
                  £{plan.originalPrice.toFixed(2)}
                </div>
              ) : null}
              {plan.duration ? (
                <div className="mt-1 font-landing-body text-xs text-site-body">
                  {plan.duration} access
                </div>
              ) : null}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-site-line">
        {relevantFeatures.map((featureName) => (
          <tr key={featureName}>
            <td className="px-6 py-3.5 font-landing-body text-sm font-medium text-site-ink">
              {featureName}
            </td>
            {Object.values(examConfig.plans).map((plan, index) => (
              <td
                key={`${featureName}-${index}`}
                className={`px-6 py-3.5 text-center font-landing-body text-sm text-site-body ${
                  plan.isPopular ? "bg-site-pale" : "bg-site-card"
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
                    return <span className="text-site-muted">-</span>;
                  }
                  if (featureName === "Feedback") {
                    return hasFeature(plan.features, alignedFeedbackLabel)
                      ? alignedFeedbackLabel
                      : <span className="text-site-muted">-</span>;
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
                    ? <span className="font-landing-mono text-base text-site-brand">✓</span>
                    : <span className="text-site-muted">-</span>;
                })()}
              </td>
            ))}
          </tr>
        ))}
        <tr>
          <td className="bg-site-pale px-6 py-5" />
          {Object.values(examConfig.plans).map((plan, index) => (
            <td
              key={`button-${index}`}
              className={`px-6 py-5 text-center ${
                "bg-site-pale"
              }`}
            >
              <SiteButton
                onClick={onSelectPlan}
                variant={plan.ctaColor === "blue" ? "brand" : "line"}
                className="w-full"
                >
                {plan.cta}
              </SiteButton>
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}
