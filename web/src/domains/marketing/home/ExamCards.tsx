import Link from "next/link";
import { SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import { EXAMS } from "@/domains/marketing/landingCopy";

export function ExamCards() {
  return (
    <Section id="exams" tone="pale" label="Exams">
      <SectionHead eyebrow={EXAMS.eyebrow} title={EXAMS.title} sub={EXAMS.sub} />
      <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {EXAMS.items.map(({ href, code, body, line }) => (
          <Link key={code} href={href} className="group flex min-w-0 flex-col rounded-2xl border border-site-line bg-site-card p-6 transition-colors hover:border-site-brand">
            <span className="font-landing-heading text-2xl font-bold text-site-ink">{code}</span>
            <span className="mt-1 text-sm font-medium text-site-muted">{body}</span>
            <span className="mt-4 flex-1 leading-relaxed text-site-body">{line}</span>
            <span className="mt-6 text-sm font-semibold text-site-brand">{EXAMS.start}</span>
          </Link>
        ))}
      </div>
    </Section>
  );
}
