import { Section } from "@/domains/marketing/home/Section";
import { SITE_CARD } from "@/domains/marketing/home/Blocks";

/** Numbers that say what the exam is: a value and the line under it. */
export function ExamFacts({ facts }: { facts: readonly { value: string; label: string }[] }) {
  return (
    <dl className="grid gap-5 sm:grid-cols-3">
      {facts.map((fact) => (
        <div key={fact.label} className={`${SITE_CARD} text-center`}>
          <dt className="sr-only">{fact.label}</dt>
          <dd>
            <span className="block font-landing-heading text-3xl font-bold text-site-brand sm:text-4xl">{fact.value}</span>
            <span className="mt-2 block text-site-body">{fact.label}</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** A passed candidate's words, set large in a card. */
export function ExamQuote({ quote, attribution }: { quote: string; attribution: string }) {
  return (
    <Section tone="pale">
      <figure className="relative mx-auto max-w-3xl overflow-hidden rounded-3xl border border-site-line bg-site-card p-7 sm:p-12">
        <span aria-hidden="true" className="absolute right-6 top-2 select-none font-landing-heading text-[120px] leading-none text-site-pale-strong">
          &rdquo;
        </span>
        <blockquote className="relative font-landing-heading text-[clamp(1.25rem,4.5vw,1.75rem)] font-medium leading-[1.4] text-site-ink">{quote}</blockquote>
        <figcaption className="relative mt-6 flex items-center gap-3 border-t border-site-line pt-5 font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] text-site-brand">
          <span aria-hidden="true" className="h-px w-8 shrink-0 bg-site-brand" />
          {attribution}
        </figcaption>
      </figure>
    </Section>
  );
}
