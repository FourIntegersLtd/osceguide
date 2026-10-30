"use client";

import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks/useAsync";
import { EXAM_CONFIGS, type ExamConfig, type ExamName } from "./pricingContent";
import { ExamTabs } from "./ExamTabs";
import { PricingCards } from "./PricingCards";
import { PricingTable, type PricingTableProps } from "./PricingTable";
import { Eyebrow, SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import type { ExamKey } from "./landingExams";
import { readPlansOnSale } from "@/domains/marketing/api";
import { livePricedPlans } from "@/domains/marketing/support/livePlans";
import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";

export type PricedConfig = ExamConfig & { plans: NonNullable<ExamConfig["plans"]> };

/**
 * The exam's plans priced from the plans on sale (a failed read shows no price at all), or a short line saying why not.
 * `children` lays the priced plans out.
 */
export function PricedExam({ examName, config, children }: { examName: string; config: PricedConfig; children: (priced: PricedConfig) => ReactNode }) {
  const live = useAsync(async (signal) => (await readPlansOnSale(signal)).items, []);
  return (
    <AsyncBoundary
      state={live}
      loading={<p className="text-center text-site-body">Loading prices…</p>}
      failure={() => (
        <p role="alert" className="text-center text-site-body">
          We could not load prices just now. Please refresh, or try again shortly.
        </p>
      )}
    >
      {(plansOnSale) => {
        const plans = livePricedPlans(config.plans, examName.toLowerCase(), plansOnSale);
        if (Object.keys(plans).length <= 1) {
          return <PricingComingSoon examName={config.name} label={config.label} />;
        }
        return children({ ...config, plans });
      }}
    </AsyncBoundary>
  );
}

function PricingComparisonLayout({ examConfig, onSelectPlan }: PricingTableProps) {
  return (
    <>
      <div className="hidden md:block">
        <div className="overflow-x-auto rounded-2xl border border-site-line bg-site-card">
          <PricingTable
            examConfig={examConfig}
            onSelectPlan={onSelectPlan}
          />
        </div>
      </div>
      <div className="mt-8 md:hidden">
        <PricingCards
          examConfig={examConfig}
          onSelectPlan={onSelectPlan}
        />
      </div>
    </>
  );
}

/** `asPageTitle`: the section is the whole page (`/pricing`), so its heading is the h1. */
export function PricingSectionContent({ asPageTitle = false }: { asPageTitle?: boolean }) {
  const router = useRouter();
  const partner = usePartnerContext();
  const [selectedExam, setSelectedExam] = useState<ExamName>("SCA");

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
    <PricedExam examName={selectedExam} config={plansConfig}>
      {(priced) => <PricingComparisonLayout examConfig={priced} onSelectPlan={() => handleNavigation(selectedExam)} />}
    </PricedExam>
  ) : (
    <PricingComingSoon
      examName={currentExamConfig.name}
      label={currentExamConfig.label}
    />
  );

  return (
    <Section id="pricing">
      <SectionHead
        as={asPageTitle ? "h1" : "h2"}
        title={<>Simple, Transparent <span className="text-site-brand">Pricing</span></>}
        sub="Choose your exam"
      />
      <div className="mt-10">
        <ExamTabs selected={selectedExam} onSelect={setSelectedExam} />
        {pricingContent}
      </div>
    </Section>
  );
}

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
  const examKey = APP_TYPE_TO_EXAM[appType];
  const examConfig = examKey ? (EXAM_CONFIGS[examKey] as ExamConfig | undefined) : undefined;

  if (!examConfig?.plans) {
    return null;
  }

  const plansConfig = examConfig as ExamConfig & {
    plans: NonNullable<ExamConfig["plans"]>;
  };

  return (
    <Section id="pricing">
      <SectionHead
        title={<>Choose Your <span className="text-site-brand">Plan</span></>}
        sub={`Flexible pricing options to suit your ${examConfig.name} preparation`}
      />
      <div className="mt-10">
        <PricedExam examName={examKey} config={plansConfig}>
          {(priced) => <PricingComparisonLayout examConfig={priced} onSelectPlan={() => router.push(partner.href(REGISTER_PATH, appType))} />}
        </PricedExam>
      </div>
    </Section>
  );
}

// --- Helper Components ---

export function PricingComingSoon({ examName, label }: { examName: string; label: string }) {
  return (
    <div className="mx-auto max-w-[880px] overflow-hidden rounded-2xl border border-site-line bg-site-card px-8 py-12 text-center">
      <Eyebrow>Coming soon</Eyebrow>
      <h3 className="mt-3 font-landing-heading text-2xl font-bold text-site-ink">
        {examName} pricing
      </h3>
      <p className="mt-3 text-site-body">
        {label}. Plans and pricing for this exam will be available here soon.
      </p>
    </div>
  );
}

