"use client";

import { useState } from "react";
import { FiCheck } from "react-icons/fi";
import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { useAsync } from "@/foundation/hooks/useAsync";
import { AsyncBoundary } from "@/foundation/ui";
import { readPlansOnSale } from "@/domains/marketing/api";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { Section } from "@/domains/marketing/home/Section";
import { getPlanCardFeatures } from "@/domains/marketing/PricingCards";
import { EXAM_CONFIGS, type ExamConfig, type ExamName } from "@/domains/marketing/pricingContent";
import { livePricedPlans } from "@/domains/marketing/support/livePlans";

const EXAMS = Object.keys(EXAM_CONFIGS) as ExamName[];

function Plans({ exam, config }: { exam: ExamName; config: ExamConfig & { plans: NonNullable<ExamConfig["plans"]> } }) {
  const live = useAsync(async (signal) => (await readPlansOnSale(signal)).items, []);
  return (
    <AsyncBoundary
      state={live}
      loading={<p className="mt-10 text-site-body">Loading prices…</p>}
      failure={() => (
        <p role="alert" className="mt-10 text-site-body">
          We could not load prices just now. Please refresh, or try again shortly.
        </p>
      )}
    >
      {(onSale) => {
        const plans = livePricedPlans(config.plans, exam.toLowerCase(), onSale);
        const entries = Object.entries(plans);
        if (entries.length <= 1) return <ComingSoon config={config} />;
        return (
          <div className="mt-10 grid gap-4 text-left sm:grid-cols-2 lg:grid-cols-4">
            {entries.map(([key, plan]) => {
              const free = plan.price <= 0;
              return (
                <div
                  key={key}
                  className={`relative flex flex-col rounded-2xl border p-6 ${
                    free ? "border-transparent bg-site-navy text-white" : plan.isPopular ? "border-site-brand bg-site-card" : "border-site-line bg-site-card"
                  }`}
                >
                  {plan.isPopular && (
                    <span className="absolute -top-3 left-6 rounded-full bg-site-brand px-3 py-0.5 text-xs font-semibold text-site-on-brand">Most chosen</span>
                  )}
                  <h3 className={`font-landing-heading text-lg font-bold ${free ? "text-white" : "text-site-ink"}`}>{plan.name}</h3>
                  <div className={`mt-3 font-landing-mono text-3xl font-medium ${free ? "text-white" : "text-site-ink"}`}>
                    {free ? "Free" : `£${plan.price.toFixed(2)}`}
                    {plan.originalPrice ? <s className="ml-2 text-sm text-site-faint">£{plan.originalPrice.toFixed(2)}</s> : null}
                  </div>
                  {plan.duration && <p className={`mt-1 text-sm ${free ? "text-site-on-navy" : "text-site-muted"}`}>{plan.duration} access</p>}
                  <ul className="my-5 flex-1 space-y-2 text-sm">
                    {getPlanCardFeatures(config, plan.features).map((f) => (
                      <li key={f} className={`flex items-start gap-2 ${free ? "text-site-on-navy" : "text-site-body"}`}>
                        <FiCheck aria-hidden className="mt-0.5 shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <PartnerLink path={REGISTER_PATH} exam={exam.toLowerCase()} variant={free ? "white" : plan.isPopular ? "brand" : "line"}>
                    {plan.cta}
                  </PartnerLink>
                </div>
              );
            })}
          </div>
        );
      }}
    </AsyncBoundary>
  );
}

function ComingSoon({ config }: { config: ExamConfig }) {
  return (
    <div className="mx-auto mt-10 max-w-xl rounded-2xl border border-site-line bg-site-card px-8 py-12">
      <p className="font-landing-mono text-[11px] uppercase tracking-[0.13em] text-site-brand">Coming soon</p>
      <h3 className="mt-3 font-landing-heading text-2xl font-bold text-site-ink">{config.name} pricing</h3>
      <p className="mt-3 text-site-body">{config.label}. Plans and pricing for this exam will be available here soon.</p>
    </div>
  );
}

export function HomePricing() {
  const [exam, setExam] = useState<ExamName>("SCA");
  const config: ExamConfig = EXAM_CONFIGS[exam];
  const priced = config.plans ? { ...config, plans: config.plans } : null;

  return (
    <Section id="pricing">
      <div className="text-center">
        <h2 className="mx-auto max-w-3xl font-landing-heading text-3xl font-bold leading-tight text-site-ink sm:text-4xl">
          Flexible pricing options to suit your <span className="text-site-brand">{config.name}</span> preparation
        </h2>
        <div role="tablist" aria-label="Exam" className="mt-8 flex justify-center">
          <div className="inline-flex max-w-full flex-wrap justify-center gap-1 rounded-3xl bg-site-pale p-1">
            {EXAMS.map((name) => (
              <button
                key={name}
                type="button"
                role="tab"
                aria-selected={exam === name}
                onClick={() => setExam(name)}
                className={`h-11 whitespace-nowrap rounded-full px-4 sm:px-5 text-sm font-semibold transition-colors ${
                  exam === name ? "bg-site-card text-site-brand shadow-sm" : "text-site-muted hover:text-site-ink"
                }`}
              >
                {EXAM_CONFIGS[name].name}
              </button>
            ))}
          </div>
        </div>
        {priced ? <Plans exam={exam} config={priced} /> : <ComingSoon config={config} />}
      </div>
    </Section>
  );
}
