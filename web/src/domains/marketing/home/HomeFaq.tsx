import { FAQ_ITEMS } from "@/domains/marketing/home/faqItems";
import { SectionHead } from "@/foundation/ui";
import { Accordion } from "@/domains/marketing/home/Accordion";
import { Section } from "@/domains/marketing/home/Section";

const ITEMS = FAQ_ITEMS.map((item) => ({ title: item.question, body: item.answer }));

/** One boxed, centred column of questions, the first answer open. */
export function HomeFaq() {
  return (
    <Section id="faq" tone="card">
      <SectionHead title="Frequently asked questions" />
      <Accordion
        items={ITEMS}
        openFirst
        className="mx-auto mt-14 max-w-3xl divide-y divide-site-line rounded-2xl border border-site-line bg-site-ground"
        itemClassName="px-5 py-4"
        bodyClassName="mt-3"
      />
    </Section>
  );
}
