import { SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import { QuoteCard } from "@/domains/marketing/home/QuoteCard";
import { STORIES, STORIES_HEAD } from "@/domains/marketing/landingCopy";

/** Six stories in a static grid, no carousel. `#testimonials` and its alias `#stories` land here. */
export function TestimonialGrid() {
  return (
    <Section id="testimonials" tone="ground" label="Stories">
      <span id="stories" className="absolute -mt-24" aria-hidden />
      <SectionHead eyebrow={STORIES_HEAD.eyebrow} title={STORIES_HEAD.title} />
      <div className="mt-16 grid gap-4 md:grid-cols-3">
        {STORIES.map((q) => (
          <QuoteCard key={q.name} q={q} className="rounded-2xl border border-site-line bg-site-card p-6" />
        ))}
      </div>
    </Section>
  );
}
