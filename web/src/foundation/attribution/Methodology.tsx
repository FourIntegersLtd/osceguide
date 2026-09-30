"use client";

import type { IconType } from "react-icons";
import {
  HiOutlineBanknotes,
  HiOutlineCalculator,
  HiOutlineCalendarDays,
  HiOutlineClock,
  HiOutlineCreditCard,
  HiOutlineCursorArrowRays,
  HiOutlineFingerPrint,
  HiOutlineFunnel,
  HiOutlineLink,
  HiOutlineReceiptPercent,
  HiOutlineScale,
  HiOutlineShieldCheck,
  HiOutlineUserPlus,
} from "react-icons/hi2";
import { DefinitionCard } from "@/foundation/attribution/MetricCard";
import type { DashboardCopy, MethodologyDefinition } from "@/foundation/attribution/copy";
import type { AttributionMode } from "@/foundation/attribution/types";
import { visibleDefinitions, type MetricTone } from "@/foundation/attribution/viewModel";

const DEFINITION_ICONS: Record<string, IconType> = {
  "Link visit": HiOutlineLink,
  "Unique people": HiOutlineFingerPrint,
  "Sign-up": HiOutlineUserPlus,
  Paid: HiOutlineCreditCard,
  Revenue: HiOutlineBanknotes,
  "Est. BMJ spend": HiOutlineReceiptPercent,
  "Estimated fee": HiOutlineReceiptPercent,
  "Money left over": HiOutlineScale,
  "Spend per sign-up": HiOutlineCalculator,
};

const RULE_ICONS: Record<string, IconType> = {
  "Which link gets credit": HiOutlineCursorArrowRays,
  "How long we remember a visit": HiOutlineClock,
  "Date range": HiOutlineCalendarDays,
  Filters: HiOutlineFunnel,
};

const DEFINITION_TONES: Record<string, MetricTone> = {
  "Link visit": "orange",
  "Unique people": "amber",
  "Sign-up": "orange",
  Paid: "emerald",
  Revenue: "amber",
  "Est. BMJ spend": "orange",
  "Money left over": "emerald",
  "Spend per sign-up": "amber",
};

const RULE_TONES: Record<string, MetricTone> = {
  "Which link gets credit": "orange",
  "How long we remember a visit": "amber",
  "Date range": "orange",
  Filters: "amber",
};

function List({
  items,
  icons,
  tones,
}: {
  items: MethodologyDefinition[];
  icons: Record<string, IconType>;
  tones: Record<string, MetricTone>;
}) {
  return (
    <dl className="space-y-3">
      {items.map((item) => (
        <DefinitionCard
          key={item.term}
          term={item.term}
          detail={item.detail}
          icon={icons[item.term] ?? HiOutlineLink}
          tone={tones[item.term] ?? "amber"}
        />
      ))}
    </dl>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <section className="rounded-osce-lg border border-border bg-surface p-5 sm:p-6">
      {children}
    </section>
  );
}

/** Plain-English rules behind the numbers. A partner reads only the definitions meant for them. */
export function Methodology({
  copy,
  mode,
}: {
  copy: DashboardCopy["methodology"];
  mode: AttributionMode;
}) {
  return (
    <div className="min-w-0 space-y-5">
      <Card>
        <div className="flex gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-osce-lg bg-accent-subtle text-accent">
            <HiOutlineShieldCheck className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <p className="text-osce-caption font-medium uppercase tracking-wide text-ink-subtle">
              Plain English
            </p>
            <h2 className="mt-0.5 font-heading text-osce-subheading font-semibold text-ink">
              {copy.introTitle}
            </h2>
            <p className="mt-2 text-osce-meta text-ink-subtle">{copy.introBody}</p>
          </div>
        </div>
      </Card>
      <Card>
        <h3 className="font-heading text-osce-subheading font-semibold text-ink">
          {copy.definitionsHeading}
        </h3>
        <div className="mt-4">
          <List
            items={visibleDefinitions(mode, copy.definitions)}
            icons={DEFINITION_ICONS}
            tones={DEFINITION_TONES}
          />
        </div>
      </Card>
      <Card>
        <h3 className="font-heading text-osce-subheading font-semibold text-ink">
          {copy.rulesHeading}
        </h3>
        <div className="mt-4">
          <List items={copy.rules} icons={RULE_ICONS} tones={RULE_TONES} />
        </div>
      </Card>
    </div>
  );
}
