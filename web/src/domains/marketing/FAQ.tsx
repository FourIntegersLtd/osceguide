"use client";

import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";

const DEFAULT_FAQ_ITEMS = [
  {
    question: "What is OSCE Guide?",
    answer:
      "OSCE Guide is a Voice AI–powered simulation tool designed to help doctors prepare for their clinical simulation exams. It offers the ability to design mock exam sessions, providing realistic patient simulations, management approaches, and automated feedback to improve clinical reasoning, communication, and time management skills. All our management plans are based on evidence-based guidelines and are designed by doctors.",
  },
  {
    question:
      "What makes OSCE Guide different from other OSCE preparation tools?",
    answer:
      "OSCE Guide revolutionizes OSCE preparation through advanced Voice AI technology that enables natural, dynamic doctor-patient conversations. Unlike traditional tools, we offer real-time voice interactions, personalized feedback aligned with relevant UK clinical guidelines, and evidence-based management plans curated by practicing doctors. Our platform also provides detailed analytics to track your progress across all assessment areas, making your preparation more focused and effective.",
  },
  {
    question: "What is Practice with Colleagues?",
    answer:
      "Practice with Colleagues lets you rehearse clinical scenarios with other doctors over live video. You can get matched instantly for an on-the-spot practice session or use the Marketplace to post your availability and schedule sessions at times that suit you. Each session uses our built-in timer so you practise under exam-like conditions, and you can run through the same cases you use with our AI, with a colleague playing the patient or the doctor.",
  },
  {
    question: "How does OSCE Guide ensure the feedback is reliable?",
    answer:
      "OSCE Guide provides reliable feedback through two mechanisms: standardized assessment based on real-world clinical scenarios and AI-powered analysis of your performance. This dual approach ensures you receive consistent feedback that aligns with the most up-to-date clinical guidelines.",
  },
  {
    question: "How does OSCE Guide handle time management for mock exams?",
    answer:
      "We incorporate a timer for each station, replicating the time constraints of the actual OSCE exams. Users can complete a full mock exam under timed conditions and receive feedback. This feature ensures you practice in an environment that closely resembles the actual exam.",
  },
  {
    question:
      "What type of data does OSCE Guide collect, and how is it protected?",
    answer:
      "OSCE Guide collects minimal user data and no personal patient data is used. We are GDPR compliant, and have robust data protection measures in place.",
  },
  {
    question: "Does OSCE Guide have a mobile app?",
    answer:
      "OSCE Guide is a Progressive Web App (PWA), which means you can install it on your home screen just like a native app. You should see an install prompt when visiting the site. For iOS devices, use Safari and follow the installation steps. For Android devices, use Chrome. If you don't see the install prompt, try opening the site in an incognito/private tab.",
  },
];

export type FAQItem = { question: string; answer: string };
type FAQSectionProps = { items?: FAQItem[] };

export function FAQSection({ items = DEFAULT_FAQ_ITEMS }: FAQSectionProps) {
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
