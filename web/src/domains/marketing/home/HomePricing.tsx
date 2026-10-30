"use client";

import { useState } from "react";
import { FiCheck } from "react-icons/fi";
import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { Section } from "@/domains/marketing/home/Section";
import { ExamTabs } from "@/domains/marketing/ExamTabs";
import { PricedExam, PricingComingSoon, type PricedConfig } from "@/domains/marketing/Pricing";
import { getPlanCardFeatures } from "@/domains/marketing/PricingCards";
import { EXAM_CONFIGS, type ExamName } from "@/domains/marketing/pricingContent";

function PlanCards({ exam, config }: { exam: ExamName; config: PricedConfig }) {
  return (
    <div className="grid gap-4 text-left sm:grid-cols-2 lg:grid-cols-4">
      {Object.entries(config.plans).map(([key, plan]) => {
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
}

export function HomePricing() {
  const [exam, setExam] = useState<ExamName>("SCA");
  const config = EXAM_CONFIGS[exam];
  const priced = config.plans ? { ...config, plans: config.plans } : null;

  return (
    <Section id="pricing">
      <div className="text-center">
        <h2 className="mx-auto max-w-3xl font-landing-heading text-3xl font-bold leading-tight text-site-ink sm:text-4xl">
          Flexible pricing options to suit your <span className="text-site-brand">{config.name}</span> preparation
        </h2>
        <div className="mt-8">
          <ExamTabs selected={exam} onSelect={setExam} />
        </div>
        <div className="mt-10">
          {priced ? (
            <PricedExam examName={exam} config={priced}>
              {(plans) => <PlanCards exam={exam} config={plans} />}
            </PricedExam>
          ) : (
            <PricingComingSoon examName={config.name} label={config.label} />
          )}
        </div>
      </div>
    </Section>
  );
}
