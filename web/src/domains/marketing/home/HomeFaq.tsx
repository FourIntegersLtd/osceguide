import { FiChevronDown } from "react-icons/fi";
import { FAQ_ITEMS } from "@/domains/marketing/home/faqItems";
import { SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";

/** `openFirst` opens the first answer, as the exam pages do. */
export function HomeFaq({ openFirst = false }: { openFirst?: boolean }) {
  return (
    <Section id="faq" tone="card">
      <SectionHead title="Frequently asked questions" />
      <div className="mx-auto mt-10 max-w-3xl divide-y divide-site-line rounded-2xl border border-site-line bg-site-ground">
        {FAQ_ITEMS.map((item, i) => (
          <details key={item.question} open={openFirst && i === 0} className="group px-5 py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-site-ink [&::-webkit-details-marker]:hidden">
              {item.question}
              <FiChevronDown aria-hidden className="shrink-0 transition-transform group-open:rotate-180" />
            </summary>
            <p className="mt-3 leading-relaxed text-site-body">{item.answer}</p>
          </details>
        ))}
      </div>
    </Section>
  );
}
