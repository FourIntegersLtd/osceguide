"use client";

import {
  HiOutlineBeaker,
  HiOutlineBookOpen,
  HiOutlineBriefcase,
  HiOutlineChatBubbleLeftRight,
  HiOutlineClipboardDocumentList,
  HiOutlineExclamationTriangle,
  HiOutlineHeart,
  HiOutlineHome,
  HiOutlineMagnifyingGlass,
  HiOutlineUsers,
} from "react-icons/hi2";
import { LuBaby, LuBrain, LuHeartHandshake } from "react-icons/lu";
import type { IconType } from "react-icons";
import type { ReactNode } from "react";
import { cn, productTokens as t } from "@/foundation/ui";
import type { SummarySection } from "@/capabilities/media/api";
import { boldLead } from "@/capabilities/media/support/text";

const CLINICAL: Record<SummarySection["key"], { title: string; icon: IconType; tone: keyof typeof t.b2cReadingTones }> = {
  red_flags: { title: "Red Flags", icon: HiOutlineExclamationTriangle, tone: "safety" },
  examinations: { title: "Examinations & Investigations", icon: HiOutlineBeaker, tone: "examination" },
  brief_management: { title: "Management Plan", icon: HiOutlineClipboardDocumentList, tone: "management" },
};

const ASPECT_ICONS: IconType[] = [
  HiOutlineUsers,
  HiOutlineBookOpen,
  HiOutlineMagnifyingGlass,
  HiOutlineHeart,
  HiOutlineChatBubbleLeftRight,
  HiOutlineHome,
  HiOutlineBriefcase,
  LuHeartHandshake,
  LuBrain,
  LuBaby,
];

/**
 * One tinted block (canvas `train-summary`): no border (the tone's card
 * class only colours one), the heading in the tone's ink, the list in body text.
 */
function ToneBlock({
  tone,
  icon: Icon,
  title,
  children,
  className,
}: {
  tone: keyof typeof t.b2cReadingTones;
  icon: IconType;
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <article className={cn("w-full rounded-osce-lg px-[18px] py-4", t.b2cReadingTones[tone].card, className)}>
      <h2 className={cn("flex items-center gap-2 text-osce-body font-semibold", t.b2cReadingTones[tone].title)}>
        <Icon className="h-4 w-4 shrink-0" aria-hidden />
        {title}
      </h2>
      <div className="mt-2 text-osce-body leading-[22px] text-osce-ink-700">{children}</div>
    </article>
  );
}

/** One list item with its `Label:` in bold. */
function ListEntry({ entry }: { entry: string }) {
  const { lead, rest } = boldLead(entry);
  return (
    <li className="leading-[22px]">
      {lead ? <strong className="font-semibold text-osce-ink-900">{lead} </strong> : null}
      {rest}
    </li>
  );
}

function EntryList({ entries }: { entries: string[] }) {
  return (
    <ul className="list-disc space-y-2 pl-[18px]">
      {entries.map((entry, index) => (
        <ListEntry key={index} entry={entry} />
      ))}
    </ul>
  );
}

export function ClinicalSections({ sections }: { sections: SummarySection[] }) {
  return (
    <div className="grid w-full gap-4 md:grid-cols-2">
      {sections.map((section) => {
        const meta = CLINICAL[section.key];
        return (
          <ToneBlock
            key={section.key}
            tone={meta.tone}
            icon={meta.icon}
            title={meta.title}
            className={section.key === "brief_management" ? "md:col-span-2" : undefined}
          >
            <EntryList entries={section.items} />
          </ToneBlock>
        );
      })}
    </div>
  );
}

/**
 * An aspect is stored as `Title: one; two; three`, which is how the retiring
 * authoring tool wrote it. Parsed rather than printed raw, so a summary
 * published against either backend reads the same.
 */
function splitAspect(aspect: string): { title: string; items: string[] } {
  const colon = aspect.indexOf(": ");
  if (colon === -1) return { title: aspect, items: [] };
  const title = aspect.slice(0, colon);
  const details = aspect.slice(colon + 2);
  return {
    title,
    items: details
      .split(";")
      .map((entry) => entry.trim())
      .filter(Boolean)
      .map((entry) => entry.charAt(0).toUpperCase() + entry.slice(1)),
  };
}

export function PsychosocialSections({ aspects }: { aspects: string[] }) {
  if (aspects.length === 0) {
    return <p className={t.b2cBodyTextMuted}>No psychosocial information available</p>;
  }

  return (
    <div className="grid w-full items-stretch gap-4 md:grid-cols-2">
      {aspects.map((aspect, index) => {
        const { title, items } = splitAspect(aspect);
        const toneKey =
          t.b2cPsychosocialReadingToneKeys[index % t.b2cPsychosocialReadingToneKeys.length] ??
          "history";
        const Icon = ASPECT_ICONS[index % ASPECT_ICONS.length] ?? HiOutlineUsers;

        return (
          <ToneBlock key={index} tone={toneKey} icon={Icon} title={title}>
            {items.length > 0 ? <EntryList entries={items} /> : null}
          </ToneBlock>
        );
      })}
    </div>
  );
}
