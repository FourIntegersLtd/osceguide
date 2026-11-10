import { FAQ_ITEMS } from "@/domains/marketing/home/faqItems";
import { SectionHead } from "@/foundation/ui";
import { Accordion } from "@/domains/marketing/home/Accordion";
import { Section } from "@/domains/marketing/home/Section";

const ITEMS = FAQ_ITEMS.map((item) => ({ title: item.question, body: item.answer }));

/** `openFirst` opens the first answer. `split` lays the questions in two ruled columns from lg up; otherwise one boxed list. */
export function HomeFaq({ openFirst = false, split = false }: { openFirst?: boolean; split?: boolean }) {
  return (
    <Section id="faq" tone={split ? "ground" : "card"}>
      <SectionHead title="Frequently asked questions" />
      <Accordion
        items={ITEMS}
        openFirst={openFirst}
        className={split ? "mt-10 grid gap-x-10 lg:mt-14 lg:grid-cols-2" : "mx-auto mt-14 max-w-3xl divide-y divide-site-line rounded-2xl border border-site-line bg-site-ground"}
        itemClassName={split ? "border-t border-site-line py-4 lg:[&:nth-last-child(-n+2)]:border-b" : "px-5 py-4"}
        bodyClassName="mt-3"
      />
    </Section>
  );
}
