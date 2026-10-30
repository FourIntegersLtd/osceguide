import { FiMessageSquare } from "react-icons/fi";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { SiteButtonLink } from "@/foundation/ui";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { IconTile, SectionHead } from "@/foundation/ui";
import { FOUNDERS_LETTER } from "@/domains/marketing/foundersLetter";
import { Section } from "@/domains/marketing/home/Section";
import { MARQUEE_TESTIMONIALS, type MarqueeTestimonial } from "@/domains/marketing/support/testimonials";

export function HomeFounders() {
  return (
    <Section>
      <article className="mx-auto max-w-3xl rounded-3xl border border-site-line bg-site-card p-6 sm:p-10">
        <div className="flex items-center gap-3">
          <IconTile><FiMessageSquare /></IconTile>
          <span className="font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] text-site-brand">A message from our founders</span>
        </div>
        <div className="mt-6 space-y-4 text-[17px] leading-[1.7] text-site-body">
          {FOUNDERS_LETTER.map((t) => <p key={t}>{t}</p>)}
        </div>
        <p className="mt-7 border-t border-site-line pt-6">
          <b className="text-site-ink">Kenny and Aisha</b>, <span className="text-site-muted">Co-founders</span>
        </p>
      </article>
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
export function HomeTestimonials() {
  return (
    <Section id="testimonials" tone="card">
      <SectionHead title="What our doctors say" />
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
        <PartnerLink path={LOGIN_PATH} size="lg">Start practising</PartnerLink>
        <SiteButtonLink
          href={`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent("OSCE Guide Demo")}`}
          variant="line"
          size="lg"
        >
          Book a demo
        </SiteButtonLink>
      </div>
    </Section>
  );
}
