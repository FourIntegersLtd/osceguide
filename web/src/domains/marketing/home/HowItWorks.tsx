import { SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import { Shot } from "@/domains/marketing/home/Shot";
import { LANDING_SHOTS } from "@/domains/marketing/home/landingShots";
import { STEPS } from "@/domains/marketing/landingCopy";

const SHOTS = [LANDING_SHOTS.choose, LANDING_SHOTS.consult, LANDING_SHOTS.marked] as const;
const SIZES = "(min-width: 1280px) 400px, (min-width: 768px) 33vw, 100vw";

export function HowItWorks() {
  return (
    <Section id="how" tone="ground" label="How it works">
      <SectionHead eyebrow={STEPS.eyebrow} title={STEPS.title} />
      <ol className="mt-20 grid gap-10 md:grid-cols-3 md:gap-6">
        {STEPS.items.map((step, i) => (
          <li key={step.title} className="min-w-0">
            <Shot shot={SHOTS[i]!} sizes={SIZES} />
            <h3 className="mt-6 font-landing-heading text-xl font-bold text-site-ink">
              <span className="mr-2 font-landing-mono text-sm font-medium text-site-brand">{i + 1}</span>
              {step.title}
            </h3>
          </li>
        ))}
      </ol>
    </Section>
  );
}
