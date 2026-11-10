import Image from "next/image";
import type { ReactNode } from "react";
import { FiCheck } from "react-icons/fi";
import { MARKETPLACE_VIDEO_SRC, MARKETPLACE_VIDEO_TITLE } from "@/capabilities/peer-practice/marketplace/copy";
import { DemoVideo } from "@/foundation/ui/DemoVideo";
import { AthenaAvatar, Eyebrow, SiteContainer } from "@/foundation/ui";
import { Accordion, type AccordionItem } from "@/domains/marketing/home/Accordion";
import { LANDING_SHOTS, type LandingShot } from "@/domains/marketing/home/landingShots";
import { FEATURES } from "@/domains/marketing/landingCopy";

const FRAME = "overflow-hidden rounded-t-[14px] border border-b-0 border-site-line bg-site-card shadow-xl lg:rounded-t-none lg:border-b";
/** On a phone the capture hangs off the panel's bottom edge; from lg up it bleeds off the side the text is not on. */
const BLEED_RIGHT = "lg:rounded-l-2xl lg:border-r-0";
const BLEED_LEFT = "lg:rounded-r-2xl lg:border-l-0";
const SIZES = "(min-width: 1024px) 700px, 560px";

/** A flat browser frame around a capture, cropped from its top. `lgCrop` picks the side kept from lg up. */
function CaptureFrame({ shot, side, lgCrop }: { shot: LandingShot; side: "right" | "left"; lgCrop: string }) {
  return (
    <div className={`${FRAME} ${side === "right" ? BLEED_RIGHT : BLEED_LEFT} h-[260px] lg:h-[520px]`}>
      <div aria-hidden="true" className="flex h-7 items-center gap-1.5 border-b border-site-line bg-site-ground px-3 lg:h-[34px] lg:gap-1.5 lg:px-3.5">
        {[0, 1, 2].map((i) => (
          <i key={i} className="block h-2 w-2 rounded-full bg-site-rule lg:h-[9px] lg:w-[9px]" />
        ))}
      </div>
      <div className="h-[232px] overflow-hidden lg:h-[486px]">
        <Image
          src={shot.src}
          alt={shot.alt}
          width={shot.width}
          height={shot.height}
          sizes={SIZES}
          className={`block h-full w-[160%] max-w-none object-cover object-left-top lg:w-full lg:max-w-full ${lgCrop}`}
        />
      </div>
    </div>
  );
}

function Expanders({ items }: { items: readonly AccordionItem[] }) {
  return (
    <Accordion
      items={items}
      openFirst
      className="mt-6 lg:mt-8"
      itemClassName="border-t border-site-ink/10 last:border-b"
      summaryClassName="gap-3 py-4 lg:gap-4 lg:py-[18px] lg:text-[17px] [&>svg]:text-xl"
      bodyClassName="max-w-[520px] pb-[18px] text-[15px] lg:pb-5 lg:text-base"
    />
  );
}

function CheckList({ items }: { items: readonly string[] }) {
  return (
    <ul className="mt-6 flex flex-col gap-3 font-medium text-site-ink lg:mt-7 lg:gap-3.5 lg:text-base">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-2.5 lg:gap-3">
          <span aria-hidden="true" className="inline-flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full bg-site-brand text-site-on-brand lg:h-6 lg:w-6">
            <FiCheck size={14} strokeWidth={3} />
          </span>
          {item}
        </li>
      ))}
    </ul>
  );
}

/**
 * One tinted panel: the words on one side, a visual bleeding off the other from lg up (`visualSide`),
 * and along the bottom edge on a phone. The words come first in the markup so a phone reads them first.
 */
function Panel({ id, tint, visualSide, eyebrow, avatar = false, title, lead, visual, children }: { id: string; tint: string; visualSide: "right" | "left"; eyebrow: string; avatar?: boolean; title: string; lead?: string; visual: ReactNode; children: ReactNode }) {
  const right = visualSide === "right";
  return (
    <section aria-labelledby={id} className="py-2 lg:py-6">
      <SiteContainer>
        <div
          className={`grid items-center gap-7 overflow-hidden rounded-3xl px-6 pt-8 lg:gap-14 lg:rounded-[28px] lg:py-16 ${tint} ${
            right ? "lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:pl-16 lg:pr-0" : "lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:pl-0 lg:pr-16"
          }`}
        >
          <div className={`min-w-0 ${right ? "" : "lg:order-2"}`}>
            <div className="flex items-center gap-3">
              {avatar && <AthenaAvatar className="h-10 w-10 border-2 border-site-card shadow-md" />}
              <Eyebrow>{eyebrow}</Eyebrow>
            </div>
            <h2 id={id} className="mt-3 font-landing-heading text-[30px] font-semibold leading-[1.12] tracking-tight text-site-ink lg:mt-4 lg:text-[40px]">{title}</h2>
            {lead && <p className="mt-3.5 text-[17px] leading-relaxed text-site-body lg:mt-[18px] lg:text-lg">{lead}</p>}
            {children}
          </div>
          <div className={`min-w-0 ${right ? "" : "lg:order-1"}`}>{visual}</div>
        </div>
      </SiteContainer>
    </section>
  );
}

/** The marketplace clip in a dark frame, as tall as the captures. */
function ClipFrame() {
  return (
    <div className={`${FRAME} ${BLEED_RIGHT} h-[220px] bg-site-device lg:h-[520px]`}>
      <DemoVideo src={MARKETPLACE_VIDEO_SRC} title={MARKETPLACE_VIDEO_TITLE} className="block h-full w-full bg-site-device object-contain" />
    </div>
  );
}

/** Four tinted panels, one capture each, the visual alternating sides. */
export function FeaturePanels() {
  const { feedback, athena, colleagues, timing } = FEATURES;
  return (
    <div id="features" className="scroll-mt-16 pb-12 lg:pb-24">
      <h2 className="sr-only">Features</h2>
      <Panel id="f-feedback" tint="bg-site-tint-feedback" visualSide="right" eyebrow={feedback.eyebrow} title={feedback.title} lead={feedback.body} visual={<CaptureFrame shot={LANDING_SHOTS.feedback} side="right" lgCrop="lg:object-left-top" />}>
        <Expanders items={feedback.items} />
      </Panel>
      <Panel id="f-athena" tint="bg-site-tint-athena" visualSide="left" eyebrow={athena.eyebrow} avatar title={athena.title} lead={athena.body} visual={<CaptureFrame shot={LANDING_SHOTS.debrief} side="left" lgCrop="lg:object-right-top" />}>
        <figure className="mt-6 rounded-[18px] border border-site-ink/10 bg-site-card p-5 lg:mt-8 lg:rounded-[20px] lg:p-6">
          <blockquote className="m-0 text-[15px] leading-relaxed text-site-body lg:text-base">&ldquo;{athena.quote.text}&rdquo;</blockquote>
          <figcaption className="mt-2.5 text-sm lg:mt-3">
            <b className="text-site-ink">{athena.quote.name}</b> <span className="text-site-muted">&middot; {athena.quote.role}</span>
          </figcaption>
        </figure>
      </Panel>
      <Panel id="f-colleagues" tint="bg-site-tint-colleagues" visualSide="right" eyebrow={colleagues.eyebrow} title={colleagues.title} visual={<ClipFrame />}>
        <Expanders items={colleagues.items} />
      </Panel>
      <Panel id="f-timing" tint="bg-site-tint-timing" visualSide="left" eyebrow="Timing" title={timing.title} lead={timing.body} visual={<CaptureFrame shot={LANDING_SHOTS.extraTime} side="left" lgCrop="lg:object-right-top" />}>
        <CheckList items={timing.checks} />
      </Panel>
    </div>
  );
}
