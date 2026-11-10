import Link from "next/link";
import { SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import { EXAMS, VISIBLE_EXAM_ITEMS } from "@/domains/marketing/landingCopy";

/** One card per offered exam (`VISIBLE_EXAMS`), each into its own page. */
export function ExamCards() {
  return (
    <Section id="exams" tone="card" label="Exams" pad="pt-16 md:pt-24">
      <SectionHead title={EXAMS.title} sub={EXAMS.sub} />
      <div className="mx-auto mt-8 grid max-w-[820px] gap-3.5 md:mt-12 md:grid-cols-2 md:gap-5">
        {VISIBLE_EXAM_ITEMS.map(({ href, code, name }) => (
          <Link key={code} href={href} className="group flex min-w-0 flex-col gap-2.5 rounded-[20px] border border-site-line bg-site-card p-7 transition-colors hover:border-site-brand">
            <span className="font-landing-heading text-[28px] font-bold leading-tight tracking-tight text-site-ink">{code}</span>
            <span className="leading-normal text-site-body">{name}</span>
            <span className="mt-2 font-semibold text-site-brand">{EXAMS.start}</span>
          </Link>
        ))}
      </div>
    </Section>
  );
}
