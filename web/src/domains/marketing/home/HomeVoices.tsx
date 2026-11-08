import type { ReactNode } from "react";
import { FiMessageSquare } from "react-icons/fi";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";
import { DEMO_MAILTO } from "@/foundation/support";
import { SiteButtonLink } from "@/foundation/ui";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { SectionHead } from "@/foundation/ui";
import { FOUNDERS_LETTER } from "@/domains/marketing/foundersLetter";
import { LetterCard } from "@/domains/marketing/home/Blocks";
import { Section } from "@/domains/marketing/home/Section";
import { MARQUEE_TESTIMONIALS, type MarqueeTestimonial } from "@/domains/marketing/support/testimonials";

export function HomeFounders() {
  return (
    <Section>
      <LetterCard
        eyebrow="A message from our founders"
        icon={<FiMessageSquare />}
        paragraphs={FOUNDERS_LETTER}
        signoff={<><b className="text-site-ink">Kenny and Aisha</b>, <span className="text-site-muted">Co-founders</span></>}
      />
    </Section>
  );
}

function Quote({ t }: { t: MarqueeTestimonial }) {
  const at = t.excerpt.indexOf(t.highlight);
  const parts = at < 0 ? [t.excerpt, "", ""] : [t.excerpt.slice(0, at), t.highlight, t.excerpt.slice(at + t.highlight.length)];
  return (
    <figure className="w-[300px] shrink-0 rounded-2xl border border-site-line bg-site-ground p-5 text-left sm:w-[360px]">
      <blockquote className="text-sm leading-relaxed text-site-body">
        &ldquo;{parts[0]}
        {parts[1] && <mark className="rounded bg-site-pale px-0.5 font-semibold text-site-brand">{parts[1]}</mark>}
        {parts[2]}&rdquo;
      </blockquote>
      <figcaption className="mt-3 text-sm">
        <b className="text-site-ink">{t.name}</b>
        <span className="block text-site-muted">{t.role}</span>
      </figcaption>
    </figure>
  );
}

/** Real quotes only, from `support/testimonials.ts`. The second copy of the row is hidden from assistive tech. */
export function HomeTestimonials({ title = "What our doctors say", ctas }: { title?: ReactNode; ctas?: ReactNode }) {
  return (
    <Section id="testimonials" tone="card">
      <SectionHead title={title} />
      <div className="site-marquee -mx-4 mt-12 overflow-hidden sm:-mx-6">
        <div className="site-marquee-track flex gap-4 px-4">
          {MARQUEE_TESTIMONIALS.map((t) => (
            <Quote key={t.name} t={t} />
          ))}
          <div aria-hidden="true" className="flex gap-4">
            {MARQUEE_TESTIMONIALS.map((t) => (
              <Quote key={t.name} t={t} />
            ))}
          </div>
        </div>
      </div>
      <div className="mt-10 flex flex-wrap justify-center gap-3">
        {ctas ?? (
          <>
            <PartnerLink path={LOGIN_PATH} size="lg">Start practising</PartnerLink>
            <SiteButtonLink
              href={DEMO_MAILTO}
              variant="line"
              size="lg"
            >
              Book a demo
            </SiteButtonLink>
          </>
        )}
      </div>
    </Section>
  );
}
