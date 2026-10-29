import { FiMessageSquare } from "react-icons/fi";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { SiteButtonLink } from "@/foundation/ui";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { IconTile, SectionHead } from "@/foundation/ui";
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
          <p>OSCE Guide was built by doctors like you. We understand the unique challenges you face because we&apos;ve been there ourselves. We know what it means to sit in that exam room and feel like your entire future depends on those few minutes.</p>
          <p>When we created OSCE Guide, we wanted to build something that truly understands the struggles of being a doctor, where the main challenge isn&apos;t the knowledge, but the ability to communicate that knowledge in a way that is clear and concise.</p>
          <p>That&apos;s why we work hard every day to create a platform that not only helps you practise, but also understands the requirements of the examiners.</p>
          <p>We built OSCE Guide on shared experiences, the same experiences that drive you to succeed. It was built by people who know what it takes to succeed in these exams, and we&apos;re here to help you do the same.</p>
        </div>
        <div className="mt-7 flex items-center gap-3 border-t border-site-line pt-6">
          <span aria-hidden="true" className="flex h-11 w-11 items-center justify-center rounded-full bg-site-pale font-landing-heading font-bold text-site-brand">A</span>
          <div>
            <b className="block text-site-ink">Aishat</b>
            <small className="text-site-muted">Co-founder, OSCE Guide</small>
          </div>
        </div>
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
      <SectionHead
        title="What our doctors say"
        sub="Doctors use OSCE Guide to practise voice-first consultations, get structured feedback, and walk into exam day ready."
      />
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
