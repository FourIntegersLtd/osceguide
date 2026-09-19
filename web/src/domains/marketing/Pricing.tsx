"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";
import { Button } from "@/foundation/ui";
import type { LandingType } from "./landingTypography";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";

const EXAM_CONFIGS = {
  SCA: {
    name: "SCA",
    label: "Structured Clinical Assessment",
    plans: {
      trial: {
        name: "Free Trial",
        stations: 3,
        duration: "2 week",
        price: 0,
        features: [
          "3 free trial stations",
          "3 attempts per station",
          "Two week access",
          "Real-Time Speech Transcription",
          "RCGP Aligned Structured Feedback",
          "Performance Analytics (Basic)",
          "Athena as Doctor",
          "Podcast Feature",
          "Debrief with Athena",
          "A to Z (Primary Care Conditions)",
        ],
        cta: "Try Now",
        ctaColor: "gray",
      },
      monthly: {
        name: "1 Month",
        stations: "50 High-Yield Clinical Scenarios",
        price: 24.99,
        features: [
          "50 High-Yield Clinical Stations",
          "3 attempts per station",
          "Real-Time Speech Transcription",
          "RCGP Aligned Structured Feedback",
          "In-Depth Performance Analytics",
          "Athena as Doctor",
          "Podcast Feature",
          "Debrief with Athena",
          "A to Z (Primary Care Conditions)",
          "Practice with Colleagues (Live Video Matching)",
          "Video Presentations",
          "PowerPoint Presentations",
        ],
        cta: "Start Now",
        ctaColor: "gray",
      },
      quarterly: {
        name: "3 Months",
        stations:  "75 High-Yield Clinical Scenarios",
        price: 64.99,
        isPopular: true,
        features: [
          "75 High-Yield Clinical Scenarios",
          "3 attempts per station",
          "Real-Time Speech Transcription",
          "RCGP Aligned Structured Feedback",
          "In-Depth Performance Analytics",
          "Athena as Doctor",
          "Podcast Feature",
          "Debrief with Athena",
          "A to Z (Primary Care Conditions)",
          "Practice with Colleagues (Live Video Matching)",
          "Video Presentations",
          "PowerPoint Presentations",
        ],
        cta: "Get Started",
        ctaColor: "blue",
      },
      sixMonth: { 
        name: "6 Months",
        stations: "100 High-Yield Clinical Scenarios", 
        price: 94.99, 
        features: [
          "100 High-Yield Clinical Scenarios",
          "3 attempts per station",
          "Real-Time Speech Transcription",
          "RCGP Aligned Structured Feedback",
          "In-Depth Performance Analytics",
          "Athena as Doctor",
          "Podcast Feature",
          "Debrief with Athena",
          "A to Z (Primary Care Conditions)",
          "Practice with Colleagues (Live Video Matching)",
          "Video Presentations",
          "PowerPoint Presentations",
        ],
        cta: "Go Premium", 
        ctaColor: "gray",
      },
    },
  },
  PLAB: {
    name: "PLAB 2",
    label: "Professional & Linguistic Assessment",
    plans: {
      trial: {
        name: "Free Trial",
        stations: 3,
        duration: "2 week",
        price: 0,
        features: [
          "3 free trial stations",
          "3 attempts per station",
          "Two week access",
          "Real-Time Speech Transcription",
          "GMC Aligned Structured Feedback",
          "Performance Analytics (Basic)",
          "Athena as Doctor",
          "Debrief with Athena",
        ],
        cta: "Try Now",
        ctaColor: "gray",
      },
      monthly: {
        name: "1 Month",
        stations: "50 High-Yield Clinical Scenarios",
        price: 24.99,
        features: [
          "50 High-Yield Clinical Stations",
          "3 attempts per station",
          "Real-Time Speech Transcription",
          "GMC Aligned Structured Feedback",
          "In-Depth Performance Analytics",
          "Athena as Doctor",
          "Debrief with Athena",
          "Practice with Colleagues (Live Video Matching)",
        ],
        cta: "Start Now",
        ctaColor: "gray",
      },
      quarterly: {
        name: "3 Months",
        stations: "75 High-Yield Clinical Scenarios",
        price: 64.99,
        isPopular: true,
        features: [
          "100+ High-Yield Clinical Scenarios",
          "3 attempts per station",
          "Real-Time Speech Transcription",
          "GMC Aligned Structured Feedback",
          "In-Depth Performance Analytics",
          "Athena as Doctor",
          "Debrief with Athena",
          "Practice with Colleagues (Live Video Matching)",
        ],
        cta: "Get Started",
        ctaColor: "blue",
      },
      sixMonth: { 
        name: "6 Months",
        stations: "100+ High-Yield Clinical Scenarios", 
        price: 94.99, 
        features: [
          "125+ High-Yield Clinical Scenarios",
          "3 attempts per station",
          "Real-Time Speech Transcription",
          "GMC Aligned Structured Feedback",
          "In-Depth Performance Analytics",
          "Athena as Doctor",
          "Debrief with Athena",
          "Practice with Colleagues (Live Video Matching)",
        ],
        cta: "Go Premium",
        ctaColor: "gray", 
      },
    },
  },
  ORTHO: {
    name: "Orthopaedics",
    label: "ST3 Interview",
    plans: {
      trial: {
        name: "Free",
        stations: 0,
        duration: "2 week",
        price: 0,
        features: [
          "Limited trial stations",
          "Clinical, prioritisation & portfolio",
          "Real-time speech transcription",
          "Basic analytics",
        ],
        cta: "Try Now",
        ctaColor: "gray",
      },
      monthly: {
        name: "1 Month",
        stations: "Full access",
        price: 24.99,
        features: [
          "All four station types (Clinical, Prioritisation, Portfolio, Communication)",
          "CV upload & personalised portfolio responses",
          "Real-time transcription",
          "In-depth analytics",
          "Practice with Colleagues (Live Video Matching)",
        ],
        cta: "Start Now",
        ctaColor: "gray",
      },
      quarterly: {
        name: "3 Months",
        stations: "Full access",
        price: 64.99,
        isPopular: true,
        features: [
          "All four station types",
          "CV upload & personalised portfolio responses",
          "Real-time transcription",
          "In-depth analytics",
          "Practice with Colleagues (Live Video Matching)",
        ],
        cta: "Get Started",
        ctaColor: "blue",
      },
      sixMonth: {
        name: "6 Months",
        stations: "Full access",
        price: 94.99,
        features: [
          "All four station types",
          "CV upload & personalised portfolio responses",
          "Real-time transcription",
          "ST3-aligned feedback",
          "In-depth analytics",
          "Practice with Colleagues (Live Video Matching)",
        ],
        cta: "Go Premium",
        ctaColor: "gray",
      },
    },
  },
  CASC: {
    name: "CASC",
    label: "Psychiatry clinical assessment",
  },
} as const;

type ExamPlan = {
  name: string;
  stations: number | string; 
  duration?: string;
  price: number;
  originalPrice?: number;
  isPopular?: boolean;
  features: readonly string[];
  cta: string;
  ctaColor: 'gray' | 'blue';
};

type ExamConfig = {
  name: string;
  label: string;
  plans?: {
    trial: ExamPlan;
    monthly: ExamPlan;
    quarterly: ExamPlan;
    sixMonth: ExamPlan; 
  };
};

type ExamName = keyof typeof EXAM_CONFIGS;


export type PricingSectionProps = {
  /** @deprecated Use LandingPricingClassicSection. */
  variant?: "default" | "premium";
};

const POPULAR_BADGE_CLASS =
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

type PricingTableProps = {
  examConfig: ExamConfig & { plans: NonNullable<ExamConfig["plans"]> };
  onSelectPlan: () => void;
  type: LandingType;
};

function PricingComparisonLayout({
  examConfig,
  onSelectPlan,
  type,
}: PricingTableProps) {
  return (
    <>
      <div className="hidden md:block">
        <div className="overflow-x-auto rounded-[var(--landing-radius-panel,14px)] border border-landing-warm bg-landing-card shadow-landing-card">
          <PricingTable
            examConfig={examConfig}
            onSelectPlan={onSelectPlan}
            type={type}
          />
        </div>
      </div>
      <div className="mt-8 md:hidden">
        <PricingCards
          examConfig={examConfig}
          onSelectPlan={onSelectPlan}
          type={type}
        />
      </div>
    </>
  );
}

export function PricingSectionContent() {
  const router = useRouter();
  const partner = usePartnerContext();
  const { type } = useLandingVariant();
  const [selectedExam, setSelectedExam] = useState<ExamName>("SCA");

  const handleNavigation = (examName: ExamName) => {
    router.push(partner.href("/auth/register", examName.toLowerCase()));
  };

  const currentExamConfig = EXAM_CONFIGS[selectedExam];

  if (!currentExamConfig) {
    return <div>Error: Exam configuration not found.</div>;
  }

  const examTabs = (
    <div className="-mx-5 mb-8 flex justify-center overflow-x-auto px-5 sm:mx-0 sm:px-0">
      <div className="inline-flex rounded-[var(--landing-radius-cta,0.5rem)] border border-landing-warm bg-[color:var(--landing-card-accent,var(--b2c-surface-muted))] p-1">
        {(Object.keys(EXAM_CONFIGS) as ExamName[]).map((examName) => {
          const examData = EXAM_CONFIGS[examName];
          const hasPlans = "plans" in examData && !!examData.plans;
          const isActive = selectedExam === examName;

          return (
            <button
              key={examName}
              type="button"
              onClick={() => setSelectedExam(examName)}
              className={`whitespace-nowrap rounded-[var(--landing-radius-cta,0.375rem)] px-4 py-2 font-landing-body text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas ${
                isActive
                  ? "border border-landing-warm bg-landing-card text-osce-ink-900 shadow-landing-card"
                  : "border border-transparent text-b2c-text-secondary hover:text-osce-ink-900"
              }`}
            >
              <span className="block">{examData.name}</span>
              {!hasPlans ? (
                <span className="hidden text-[10px] font-medium uppercase tracking-wide text-[color:var(--landing-badge-soon,#f97316)] md:block">
                  Coming soon
                </span>
              ) : (
                <span className="hidden text-xs text-b2c-text-muted md:block">
                  {examData.label}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );

  const plansConfig =
    "plans" in currentExamConfig && currentExamConfig.plans
      ? (currentExamConfig as ExamConfig & {
          plans: NonNullable<ExamConfig["plans"]>;
        })
      : null;

  const pricingContent = plansConfig ? (
    <PricingComparisonLayout
      examConfig={plansConfig}
      onSelectPlan={() => handleNavigation(selectedExam)}
      type={type}
    />
  ) : (
    <PricingComingSoon
      examName={currentExamConfig.name}
      label={currentExamConfig.label}
      type={type}
    />
  );

  return (
    <section
      id="pricing"
      className={`scroll-mt-20 ${landingSectionSurfaces.pricing} ${type.sectionPadding}`}
    >
      <div className={type.sectionShell}>
        <div className="pb-8 lg:pb-10">
          <h2 className={type.sectionTitle}>
            Simple, Transparent{" "}
            <span className="text-osce-accent">Pricing</span>
          </h2>
          <p className={type.sectionSubtitle}>Choose your exam</p>
        </div>

        {examTabs}
        {pricingContent}
      </div>
    </section>
  );
}

/** @deprecated Use LandingPricingClassicSection. */
export const PricingSection = () => {
  return <PricingSectionContent />;
};

const APP_TYPE_TO_EXAM: Record<string, ExamName> = {
  sca: "SCA",
  ortho: "ORTHO",
  plab: "PLAB",
};

export type LandingPricingSectionProps = {
  appType: "sca" | "ortho" | "plab";
};

/** Reusable pricing section for SCA, Ortho, and PLAB landing pages. Uses EXAM_CONFIGS. */
export function LandingPricingSection({ appType }: LandingPricingSectionProps) {
  const router = useRouter();
  const partner = usePartnerContext();
  const { type } = useLandingVariant();
  const examKey = APP_TYPE_TO_EXAM[appType];
  const examConfig = examKey ? (EXAM_CONFIGS[examKey] as ExamConfig | undefined) : undefined;

  if (!examConfig?.plans) {
    return null;
  }

  const plansConfig = examConfig as ExamConfig & {
    plans: NonNullable<ExamConfig["plans"]>;
  };

  return (
    <section
      id="pricing"
      className={`scroll-mt-20 ${landingSectionSurfaces.pricing} ${type.sectionPadding}`}
    >
      <div className={type.sectionShell}>
        <div className="pb-8 lg:pb-10">
          <h2 className={type.sectionTitle}>
            Choose Your <span className="text-osce-accent">Plan</span>
          </h2>
          <p className={type.sectionSubtitle}>
            Flexible pricing options to suit your {examConfig.name} preparation
          </p>
        </div>

        <PricingComparisonLayout
          examConfig={plansConfig}
          onSelectPlan={() => router.push(partner.href("/auth/register", appType))}
          type={type}
        />
      </div>
    </section>
  );
}

// --- Helper Components ---

function PricingComingSoon({
  examName,
  label,
  type,
}: {
  examName: string;
  label: string;
  type: LandingType;
}) {
  return (
    <div className="mx-auto max-w-[880px] overflow-hidden rounded-[var(--landing-radius-panel,14px)] border border-landing-warm bg-landing-card px-8 py-12 text-center shadow-landing-card">
      <p className={type.eyebrow}>Coming soon</p>
      <h3 className="mt-3 font-landing-heading text-2xl font-semibold tracking-[-0.02em] text-osce-ink-900">
        {examName} pricing
      </h3>
      <p className={`mt-3 ${type.itemBody}`}>
        {label}. Plans and pricing for this exam will be available here soon.
      </p>
    </div>
  );
}

function PricingTable({ examConfig, onSelectPlan }: PricingTableProps) {
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

function PricingCards({ examConfig, onSelectPlan, type }: PricingTableProps) {
  return (
    <div className="space-y-4">
      {Object.entries(examConfig.plans).map(([planKey, plan]) => {
        const cardFeatures = getPlanCardFeatures(examConfig, plan.features);

        return (
          <div
            key={planKey}
            className={`relative overflow-hidden rounded-[var(--landing-radius-panel,14px)] shadow-landing-card border ${
              plan.isPopular
                ? "border-osce-accent-subtle bg-landing-card-accent"
                : "border-landing-warm bg-landing-card"
            }`}
          >
            {plan.isPopular ? (
              <div className="absolute right-4 top-4 max-sm:left-4 max-sm:right-4 max-sm:flex max-sm:justify-start">
                <span className={POPULAR_BADGE_CLASS}>Most chosen</span>
              </div>
            ) : null}
            <div className={`p-6 ${plan.isPopular ? "pt-14 sm:pt-6" : ""}`}>
              <h3 className="font-landing-heading text-lg font-semibold tracking-[-0.02em] text-osce-ink-900">
                {plan.name}
              </h3>
              {plan.duration ? (
                <p className={`mt-1 ${type.itemBody}`}>{plan.duration} access</p>
              ) : null}
              <div className="mb-5 mt-3">
                <span
                  className={`font-landing-mono text-[28px] font-medium leading-none ${
                    plan.isPopular ? "text-landing-price" : "text-osce-ink-900"
                  }`}
                >
                  {plan.price > 0 ? `£${plan.price.toFixed(2)}` : "Free"}
                </span>
                {plan.originalPrice ? (
                  <span className="ml-2 font-landing-body text-sm text-b2c-text-muted line-through">
                    £{plan.originalPrice.toFixed(2)}
                  </span>
                ) : null}
              </div>
              <ul className="mb-6 space-y-2.5">
                {cardFeatures.map((feature, idx) => (
                  <li key={idx} className={`flex items-start gap-2 ${type.itemBody}`}>
                    <span className="mt-0.5 font-landing-mono text-sm text-[color:var(--landing-tick,#2CA01C)]">
                      ✓
                    </span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <Button
                onClick={onSelectPlan}
                variant={plan.ctaColor === "blue" ? "primary" : "commit"}
                size="md"
                fullWidth
              >
                {plan.cta}
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function getPlanCardFeatures(
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