"use client";

import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";
import { FAQ_ITEMS } from "./home/faqItems";

type FAQItem = { question: string; answer: string };
type FAQSectionProps = { items?: readonly FAQItem[] };

export function FAQSection({ items = FAQ_ITEMS }: FAQSectionProps) {
  const { type } = useLandingVariant();

  return (
    <section
      id="faq"
      className={`scroll-mt-20 py-16 sm:py-20 ${landingSectionSurfaces.faq}`}
    >
      <div className={`${type.sectionShell} max-w-osce-narrow`}>
        <h2 className={`${type.sectionTitle} mb-7`}>
          Frequently asked questions
        </h2>
        <div className="flex flex-col gap-3">
          {items.map((faq, index) => (
            <details
              key={faq.question}
              className="rounded-[var(--landing-radius-card,10px)] border border-landing-warm bg-landing-card shadow-landing-card transition-shadow hover:shadow-landing-card-hover"
              open={index === 0}
            >
              <summary
                className={`flex cursor-pointer list-none items-center justify-between gap-3 rounded-[var(--landing-radius-card,10px)] px-4 py-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas sm:gap-4 sm:px-[22px] sm:py-5 [&::-webkit-details-marker]:hidden ${type.faqQuestion}`}
              >
                <span>{faq.question}</span>
                <span
                  className="landing-faq-chevron text-[13px] text-osce-accent transition-transform duration-250"
                  aria-hidden
                >
                  ▾
                </span>
              </summary>
              <div className={`px-4 pb-4 sm:px-[22px] sm:pb-5 ${type.faqAnswer}`}>
                {faq.answer}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
