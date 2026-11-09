import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import { HiOutlineAdjustmentsHorizontal, HiOutlineBolt, HiOutlineCalendarDays, HiOutlineChartBar, HiOutlineChatBubbleLeftRight, HiOutlineClipboardDocumentCheck, HiOutlineClock, HiOutlineBellAlert, HiOutlineDocumentText, HiOutlinePlusCircle, HiOutlinePresentationChartLine, HiOutlineUsers } from "react-icons/hi2";
import { MARKETPLACE_VIDEO_SRC, MARKETPLACE_VIDEO_TITLE } from "@/capabilities/peer-practice/marketplace/copy";
import { DemoVideo } from "@/foundation/ui/DemoVideo";
import { Eyebrow, IconTile } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import { Frame, Shot } from "@/domains/marketing/home/Shot";
import { QuoteCard } from "@/domains/marketing/home/QuoteCard";
import { LANDING_SHOTS } from "@/domains/marketing/home/landingShots";
import { FEATURES } from "@/domains/marketing/landingCopy";

const SIZES = "(min-width: 1280px) 588px, (min-width: 1024px) 45vw, 100vw";

const FEEDBACK_ICONS = [HiOutlineClipboardDocumentCheck, HiOutlineDocumentText, HiOutlinePresentationChartLine];
const COLLEAGUE_ICONS = [HiOutlineBolt, HiOutlineCalendarDays, HiOutlineBellAlert];
const TIMING_ICONS = [HiOutlinePlusCircle, HiOutlineAdjustmentsHorizontal];

function Checks({ items, icons }: { items: readonly string[]; icons: readonly IconType[] }) {
  return (
    <ul className="mt-8 space-y-4">
      {items.map((item, i) => {
        const Icon = icons[i]!;
        return (
        <li key={item} className="flex items-start gap-3 text-site-ink">
          <Icon aria-hidden className="mt-0.5 h-6 w-6 shrink-0 text-site-brand" />
          {item}
        </li>
        );
      })}
    </ul>
  );
}

function Items({ items, icons }: { items: readonly { title: string; body: string }[]; icons: readonly IconType[] }) {
  return (
    <ul className="mt-8 space-y-6">
      {items.map((item, i) => {
        const Icon = icons[i]!;
        return (
        <li key={item.title} className="flex items-start gap-3">
          <Icon aria-hidden className="mt-0.5 h-6 w-6 shrink-0 text-site-brand" />
          <div>
            <h4 className="font-landing-heading font-bold text-site-ink">{item.title}</h4>
            <p className="text-site-body">{item.body}</p>
          </div>
        </li>
        );
      })}
    </ul>
  );
}

function Row({ Icon, eyebrow, title, body, flip = false, visual, children }: { Icon: IconType; eyebrow?: string; title: string; body?: string; flip?: boolean; visual: ReactNode; children?: ReactNode }) {
  return (
    <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-24">
      <div className={`min-w-0 ${flip ? "lg:order-2" : ""}`}>
        {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
        <div className="mt-5 flex items-center gap-3">
          <IconTile><Icon /></IconTile>
          <h3 className="text-balance font-landing-heading text-2xl font-bold leading-tight text-site-ink sm:text-3xl">{title}</h3>
        </div>
        {body && <p className="mt-6 text-[17px] leading-relaxed text-site-body">{body}</p>}
        {children}
      </div>
      <div className={`min-w-0 ${flip ? "lg:order-1" : ""}`}>{visual}</div>
    </div>
  );
}

/** Four rows, one and one real screen each, alternating sides. */
export function FeatureRows() {
  const { feedback, athena, colleagues, timing } = FEATURES;
  return (
    <Section id="features" tone="card" label="Features">
      <h2 className="sr-only">Features</h2>
      <div className="space-y-24 sm:space-y-40">
        <Row Icon={HiOutlineChartBar} title={feedback.title} eyebrow={feedback.eyebrow} body={feedback.body} visual={<Shot shot={LANDING_SHOTS.feedback} sizes={SIZES} />}>
          <Checks items={feedback.checks} icons={FEEDBACK_ICONS} />
        </Row>
        <Row Icon={HiOutlineChatBubbleLeftRight} title={athena.title} eyebrow={athena.eyebrow} body={athena.body} flip visual={<Shot shot={LANDING_SHOTS.debrief} sizes={SIZES} />}>
          <QuoteCard q={athena.quote} className="mt-8 border-l-2 border-site-line pl-4" />
        </Row>
        <Row
          Icon={HiOutlineUsers}
          eyebrow={colleagues.eyebrow}
          title={colleagues.title}
          visual={
            <Frame>
              <DemoVideo src={MARKETPLACE_VIDEO_SRC} title={MARKETPLACE_VIDEO_TITLE} className="aspect-video w-full bg-site-pale object-contain" />
            </Frame>
          }
        >
          <Items items={colleagues.items} icons={COLLEAGUE_ICONS} />
        </Row>
        <Row Icon={HiOutlineClock} title={timing.title} body={timing.body} flip visual={<Shot shot={LANDING_SHOTS.extraTime} sizes={SIZES} />}>
          <Checks items={timing.checks} icons={TIMING_ICONS} />
        </Row>
      </div>
    </Section>
  );
}
