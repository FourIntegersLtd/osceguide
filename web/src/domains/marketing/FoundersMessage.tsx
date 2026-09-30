"use client";

import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";

export function FoundersMessage() {
  const { type } = useLandingVariant();

  return (
    <section
      className={`scroll-mt-20 py-16 sm:py-20 ${landingSectionSurfaces.founders}`}
    >
      <div className={`${type.sectionShell} max-w-osce-narrow`}>
        <h2 className="font-landing-heading text-[clamp(1.5rem,2.8vw,2rem)] font-semibold leading-[1.2] tracking-[-0.025em] text-osce-ink-900">
          A message from our founders
        </h2>
        <div className="mt-6 flex flex-col gap-[18px]">
          <p className="font-landing-body text-[15px] leading-[1.7] text-landing-ink-body sm:text-[17px]">
            OSCE Guide was built by doctors like you. We understand the unique
            challenges you face because we&apos;ve been there ourselves. We know
            what it means to sit in that exam room and feel like your entire
            future depends on those few minutes.
          </p>
          <p className="font-landing-body text-[15px] leading-[1.7] text-landing-ink-body sm:text-[17px]">
            When we created OSCE Guide, we wanted to build something that truly
            understands the struggles of being a doctor, where the main challenge
            isn&apos;t the knowledge, but the ability to communicate that
            knowledge in a way that is clear and concise.
          </p>
          <p className="font-landing-body text-[15px] leading-[1.7] text-landing-ink-body sm:text-[17px]">
            That&apos;s why we work hard every day to create a platform that not
            only helps you practice, but also understands the requirements of
            the examiners.
          </p>
          <p className="font-landing-body text-[15px] leading-[1.7] text-landing-ink-body sm:text-[17px]">
            We&apos;ve built OSCE Guide based on shared experiences - the same
            experiences that drive you to succeed and we want you to evolve when
            you use OSCE Guide. Because this was built by people who know what
            it takes to succeed in these exams - and we&apos;re here to help you
            do the same.
          </p>
        </div>
        <div className="mt-7 flex items-center gap-2.5 border-t border-landing-warm pt-[22px]">
          <span className="font-landing-heading text-base font-semibold text-osce-ink-900">
            Aishat
          </span>
          <span className="font-landing-body text-[15px] text-b2c-text-secondary">
            Co-founder, OSCE Guide
          </span>
        </div>
      </div>
    </section>
  );
}

export default FoundersMessage;
