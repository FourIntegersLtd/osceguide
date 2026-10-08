"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync, type AsyncState } from "@/foundation/hooks/useAsync";
import { EXAM_CONFIGS, type ExamConfig, type ExamName } from "./pricingContent";
import { ExamTabs } from "./ExamTabs";
import { PricingCards } from "./PricingCards";
import { PricingTable, type PricingTableProps } from "./PricingTable";
import type { LandingType } from "./landingTypography";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";
import type { ExamKey } from "./landingExams";
import { readPlansOnSale } from "@/domains/marketing/api";
import { livePricedPlans, type LivePlan } from "@/domains/marketing/support/livePlans";
import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";

/** The plans on sale. Prices on every card come from here, so a failed read shows no price at all. */
function useLivePlans() {
  return useAsync(async (signal) => (await readPlansOnSale(signal)).items, []);
}

/** The exam's cards priced from the plans on sale, or a short line saying why not. */
function PricedExam({
  examName,
  config,
  live,
  onSelectPlan,
  type,
}: {
  examName: string;
  config: ExamConfig & { plans: NonNullable<ExamConfig["plans"]> };
  live: AsyncState<LivePlan[]>;
  onSelectPlan: () => void;
  type: LandingType;
}) {
  return (
    <AsyncBoundary
      state={live}
      loading={<p className={`text-center ${type.itemBody}`}>Loading prices…</p>}
      failure={() => (
        <p role="alert" className={`text-center ${type.itemBody}`}>
          We could not load prices just now. Please refresh, or try again shortly.
        </p>
      )}
    >
      {(plansOnSale) => {
        const plans = livePricedPlans(config.plans, examName.toLowerCase(), plansOnSale);
        if (Object.keys(plans).length <= 1) {
          return <PricingComingSoon examName={config.name} label={config.label} type={type} />;
        }
        return <PricingComparisonLayout examConfig={{ ...config, plans }} onSelectPlan={onSelectPlan} type={type} />;
      }}
    </AsyncBoundary>
  );
}

export type PricingSectionProps = {
  /** @deprecated Use LandingPricingClassicSection. */
  variant?: "default" | "premium";
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
  const live = useLivePlans();

  const handleNavigation = (examName: ExamName) => {
    router.push(partner.href(REGISTER_PATH, examName.toLowerCase()));
  };

  const currentExamConfig = EXAM_CONFIGS[selectedExam];

  if (!currentExamConfig) {
    return <div>Error: Exam configuration not found.</div>;
  }

  const plansConfig =
    "plans" in currentExamConfig && currentExamConfig.plans
      ? (currentExamConfig as ExamConfig & {
          plans: NonNullable<ExamConfig["plans"]>;
        })
      : null;

  const pricingContent = plansConfig ? (
    <PricedExam
      examName={selectedExam}
      config={plansConfig}
      live={live}
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

        <ExamTabs selected={selectedExam} onSelect={setSelectedExam} />
        {pricingContent}
      </div>
    </section>
  );
}

/** @deprecated Use LandingPricingClassicSection. */
export const PricingSection = () => {
  return <PricingSectionContent />;
};

const APP_TYPE_TO_EXAM: Record<ExamKey, ExamName> = {
  sca: "SCA",
  ortho: "ORTHO",
  plab: "PLAB",
  casc: "CASC",
};

export type LandingPricingSectionProps = {
  appType: ExamKey;
};

/** Reusable pricing section for the SCA, PLAB, CASC and Ortho landing pages. Uses EXAM_CONFIGS. */
export function LandingPricingSection({ appType }: LandingPricingSectionProps) {
  const router = useRouter();
  const partner = usePartnerContext();
  const { type } = useLandingVariant();
  const examKey = APP_TYPE_TO_EXAM[appType];
  const examConfig = examKey ? (EXAM_CONFIGS[examKey] as ExamConfig | undefined) : undefined;
  const live = useLivePlans();

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

        <PricedExam
          examName={examKey}
          config={plansConfig}
          live={live}
          onSelectPlan={() => router.push(partner.href(REGISTER_PATH, appType))}
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

