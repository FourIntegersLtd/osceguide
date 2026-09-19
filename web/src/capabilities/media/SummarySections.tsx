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
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  ModalHelper,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import type { SummarySection } from "@/capabilities/media/api";

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

export function ClinicalSections({ sections }: { sections: SummarySection[] }) {
  return (
    <div className="space-y-4">
      {sections.map((section) => {
        const meta = CLINICAL[section.key];
        const tone = t.b2cReadingTones[meta.tone];
        const Icon = meta.icon;
        return (
          <B2CPanelCard key={section.key} className={cn("mt-0", tone.card)}>
            <B2CPanelCardHeader className={tone.header}>
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              <span className={t.b2cSectionTitle}>{meta.title}</span>
            </B2CPanelCardHeader>
            <B2CPanelCardBody>
              <ul className={cn("list-disc space-y-2 pl-5", t.b2cBodyText, tone.list)}>
                {section.items.map((entry, index) => (
                  <li key={index}>{entry}</li>
                ))}
              </ul>
            </B2CPanelCardBody>
          </B2CPanelCard>
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
  const [title, details] = aspect.split(": ");
  if (!title || !details) return { title: aspect, items: [] };
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
    return (
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>Psychosocial</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <ModalHelper className="mt-0">No psychosocial information available</ModalHelper>
        </B2CPanelCardBody>
      </B2CPanelCard>
    );
  }

  return (
    <div className="space-y-4">
      {aspects.map((aspect, index) => {
        const { title, items } = splitAspect(aspect);
        const toneKey =
          t.b2cPsychosocialReadingToneKeys[index % t.b2cPsychosocialReadingToneKeys.length] ??
          "history";
        const tone = t.b2cReadingTones[toneKey];
        const Icon = ASPECT_ICONS[index % ASPECT_ICONS.length] ?? HiOutlineUsers;

        return (
          <B2CPanelCard key={index} className={cn("mt-0", tone.card)}>
            <B2CPanelCardHeader className={tone.header}>
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              <span className={t.b2cSectionTitle}>{title}</span>
            </B2CPanelCardHeader>
            <B2CPanelCardBody>
              {items.length > 0 ? (
                <ul className={cn("list-disc space-y-2 pl-5", t.b2cBodyText, tone.list)}>
                  {items.map((entry, idx) => (
                    <li key={idx}>{entry}</li>
                  ))}
                </ul>
              ) : (
                <p className={cn(t.b2cBodyText, tone.list)}>{title}</p>
              )}
            </B2CPanelCardBody>
          </B2CPanelCard>
        );
      })}
    </div>
  );
}
