import Link from "next/link";
import type { ReactNode } from "react";
import { FiCheck } from "react-icons/fi";
import { MARKETPLACE_VIDEO_SRC, MARKETPLACE_VIDEO_TITLE } from "@/capabilities/peer-practice/marketplace/copy";
import { DemoVideo } from "@/foundation/ui/DemoVideo";
import { Eyebrow } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import { Frame, Shot } from "@/domains/marketing/home/Shot";
import { LANDING_SHOTS } from "@/domains/marketing/home/landingShots";
import { QuoteCard } from "@/domains/marketing/home/QuoteCard";
import { FEATURES } from "@/domains/marketing/landingCopy";

const SIZES = "(min-width: 1200px) 560px, (min-width: 1024px) 45vw, 100vw";

function Checks({ items }: { items: readonly string[] }) {
  return (
    <ul className="mt-6 space-y-3">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3 text-site-ink">
          <FiCheck aria-hidden className="mt-1 shrink-0 text-site-brand" />
          {item}
        </li>
      ))}
    </ul>
  );
}

function Row({ eyebrow, title, body, flip = false, visual, children }: { eyebrow: string; title: string; body: string; flip?: boolean; visual: ReactNode; children?: ReactNode }) {
  return (
    <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
      <div className={`min-w-0 ${flip ? "lg:order-2" : ""}`}>
        <Eyebrow>{eyebrow}</Eyebrow>
        <h3 className="mt-3 text-balance font-landing-heading text-2xl font-bold leading-tight text-site-ink sm:text-3xl">{title}</h3>
        <p className="mt-4 text-[17px] leading-relaxed text-site-body">{body}</p>
        {children}
      </div>
      <div className={`min-w-0 ${flip ? "lg:order-1" : ""}`}>{visual}</div>
    </div>
  );
}

/** Four rows, one benefit and one real screen each, alternating sides. */
export function FeatureRows() {
  const { feedback, athena, colleagues, timing } = FEATURES;
  return (
    <Section id="features" tone="card" label="Features">
      <h2 className="sr-only">Features</h2>
      <div className="space-y-20 sm:space-y-28">
        <Row {...feedback} visual={<Shot shot={LANDING_SHOTS.feedback} sizes={SIZES} />}>
          <Checks items={feedback.checks} />
        </Row>
        <Row {...athena} flip visual={<Shot shot={LANDING_SHOTS.debrief} sizes={SIZES} />}>
          <QuoteCard q={athena.quote} className="mt-6 border-l-2 border-site-line pl-4" />
        </Row>
        <Row
          {...colleagues}
          visual={
            <Frame>
              <DemoVideo src={MARKETPLACE_VIDEO_SRC} title={MARKETPLACE_VIDEO_TITLE} className="aspect-video w-full bg-site-pale object-contain" />
            </Frame>
          }
        >
          <Link href="/exams/sca#practice" className="mt-6 inline-block font-semibold text-site-brand underline-offset-4 hover:underline">
            {colleagues.link} →
          </Link>
        </Row>
        <Row {...timing} flip visual={<Shot shot={LANDING_SHOTS.extraTime} sizes={SIZES} />}>
          <Checks items={timing.checks} />
        </Row>
      </div>
    </Section>
  );
}
