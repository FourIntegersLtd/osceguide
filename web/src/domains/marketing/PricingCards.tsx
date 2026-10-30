"use client";

import { SiteButton } from "@/foundation/ui";
import type { ExamConfig } from "./pricingContent";
import { POPULAR_BADGE_CLASS, type PricingTableProps } from "./PricingTable";

export function PricingCards({ examConfig, onSelectPlan }: PricingTableProps) {
  return (
    <div className="space-y-4">
      {Object.entries(examConfig.plans).map(([planKey, plan]) => {
        const cardFeatures = getPlanCardFeatures(examConfig, plan.features);

        return (
          <div
            key={planKey}
            className={`relative overflow-hidden rounded-2xl shadow-none border ${
              plan.isPopular
                ? "border-site-brand bg-site-pale"
                : "border-site-line bg-site-card"
            }`}
          >
            {plan.isPopular ? (
              <div className="absolute right-4 top-4 max-sm:left-4 max-sm:right-4 max-sm:flex max-sm:justify-start">
                <span className={POPULAR_BADGE_CLASS}>Most chosen</span>
              </div>
            ) : null}
            <div className={`p-6 ${plan.isPopular ? "pt-14 sm:pt-6" : ""}`}>
              <h3 className="font-landing-heading text-lg font-semibold tracking-[-0.02em] text-site-ink">
                {plan.name}
              </h3>
              {plan.duration ? (
                <p className="mt-1 text-site-body">{plan.duration} access</p>
              ) : null}
              <div className="mb-5 mt-3">
                <span
                  className={`font-landing-mono text-[28px] font-medium leading-none ${
                    plan.isPopular ? "text-site-brand" : "text-site-ink"
                  }`}
                >
                  {plan.price > 0 ? `£${plan.price.toFixed(2)}` : "Free"}
                </span>
                {plan.originalPrice ? (
                  <span className="ml-2 text-sm text-site-muted line-through">
                    £{plan.originalPrice.toFixed(2)}
                  </span>
                ) : null}
              </div>
              <ul className="mb-6 space-y-2.5">
                {cardFeatures.map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-site-body">
                    <span className="mt-0.5 font-landing-mono text-sm text-site-brand">
                      ✓
                    </span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <SiteButton
                onClick={onSelectPlan}
                variant={plan.ctaColor === "blue" ? "brand" : "line"}
                className="w-full"
                >
                {plan.cta}
              </SiteButton>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function getPlanCardFeatures(
  examConfig: ExamConfig,
  features: readonly string[],
): string[] {
  return features
    .filter((feature) => {
      if (feature === "RCGP Aligned Structured Feedback" && examConfig.name !== "SCA") {
        return false;
      }
      if (feature === "GMC Aligned Structured Feedback" && examConfig.name !== "PLAB 2") {
        return false;
      }
      if (feature === "Podcast Feature" && examConfig.name !== "SCA") {
        return false;
      }
      if (feature === "A to Z (Primary Care Conditions)" && examConfig.name !== "SCA") {
        return false;
      }
      return true;
    })
    .map((feature) => {
      if (feature === "Athena as Doctor") {
        return "Athena (Doctor Role)";
      }
      if (feature === "Debrief with Athena") {
        return "Athena Debrief";
      }
      return feature;
    })
    .filter((value, index, self) => self.indexOf(value) === index);
}
