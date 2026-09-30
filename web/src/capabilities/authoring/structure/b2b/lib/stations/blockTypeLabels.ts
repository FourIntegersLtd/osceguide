import type { ComponentType } from "react";
import {
  HiBars3,
  HiBars3BottomLeft,
  HiChatBubbleLeftRight,
  HiChartBarSquare,
  HiCheck,
  HiClipboardDocumentCheck,
  HiListBullet,
  HiPhoto,
  HiQueueList,
  HiRectangleStack,
  HiStopCircle,
  HiSignal,
} from "react-icons/hi2";
import type { StationBlockType } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
export type StationBlockFormsGroup = "text" | "rich" | "choices" | "scoring";
export const STATION_BLOCK_FORMS_GROUPS: { id: StationBlockFormsGroup; label: string }[] = [
  { id: "text", label: "Text" },
  { id: "rich", label: "Rich content" },
  { id: "choices", label: "Choices" },
  { id: "scoring", label: "Scoring" },
];
export type StationBlockFormsMeta = {
  type: StationBlockType;
  /** Group heading in the add-field menu. */ group: StationBlockFormsGroup;
  /** User-visible name in dropdowns and previews (exam / OSCE oriented, not generic survey wording). */ formsLabel: string;
  /** Longer explanation for the field-types info modal. */ description: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
}; /** Logical order for authoring station packs and feedback structure templates. */
export const STATION_BLOCK_FORMS_ORDER: StationBlockFormsMeta[] = [
  {
    type: "shortText",
    group: "text",
    formsLabel: "Short text",
    description: "One line of text. Good for names, dates, or brief answers.",
    icon: HiBars3BottomLeft,
  },
  {
    type: "longText",
    group: "text",
    formsLabel: "Long text",
    description:
      "A box for several lines of text. Good for histories, notes, or longer answers.",
    icon: HiBars3,
  },
  {
    type: "list",
    group: "text",
    formsLabel: "List",
    description:
      "Add as many bullet points as needed. Good for drug lists, ideas, or open items.",
    icon: HiListBullet,
  },
  {
    type: "media",
    group: "rich",
    formsLabel: "Media",
    description:
      "Images, audio, video or PDFs, each with an optional caption. Good for radiographs, scans, heart sounds and letters.",
    icon: HiPhoto,
  },
  {
    type: "records",
    group: "rich",
    formsLabel: "Records",
    description:
      "A card per record with the columns you set. Good for a ward list of patients, each with age, summary and notes.",
    icon: HiRectangleStack,
  },
  {
    type: "qaList",
    group: "rich",
    formsLabel: "Questions and answers",
    description: "Numbered questions, each with its model answer. Good for viva or interview questions.",
    icon: HiChatBubbleLeftRight,
  },
  {
    type: "groupedList",
    group: "rich",
    formsLabel: "Grouped list",
    description:
      "Items under headings, each with optional reasons. Good for a suggested order split by theatre list.",
    icon: HiQueueList,
  },
  {
    type: "singleSelect",
    group: "choices",
    formsLabel: "Pick one",
    description:
      "Choose one option from a list you set. Good for yes/no, gender, or a single choice.",
    icon: HiStopCircle,
  },
  {
    type: "multiSelect",
    group: "choices",
    formsLabel: "Pick several",
    description:
      "Tick any options that apply. Good when more than one answer is allowed.",
    icon: HiCheck,
  },
  {
    type: "checklist",
    group: "choices",
    formsLabel: "Checklist",
    description:
      "A fixed list of items to tick off. Good for observation lists or marking criteria.",
    icon: HiClipboardDocumentCheck,
  },
  {
    type: "scale",
    group: "scoring",
    formsLabel: "Scale",
    description:
      "Rate something on a number scale (e.g. 1–5). Good for confidence or graded scores.",
    icon: HiChartBarSquare,
  },
  {
    type: "ragCriterion",
    group: "scoring",
    formsLabel: "R/A/G criterion",
    description:
      "Red, Amber, or Green score with supporting phrase and explanation — one SCA toolkit skill.",
    icon: HiSignal,
  },
];
/** Which widgets make sense for each template kind. A patient script is prose and
 * lists; ticks, scales and R/A/G scores belong on a marking form. */
export type TemplateKind = "station" | "feedback";
export const BLOCK_TYPES_FOR_KIND: Record<TemplateKind, readonly StationBlockType[]> = {
  station: ["shortText", "longText", "list", "singleSelect", "media", "records", "qaList", "groupedList"],
  feedback: ["shortText", "longText", "list", "singleSelect", "multiSelect", "checklist", "scale", "ragCriterion"],
};
export function formsOrderForKind(kind: TemplateKind): StationBlockFormsMeta[] {
  const allowed = new Set(BLOCK_TYPES_FOR_KIND[kind]);
  return STATION_BLOCK_FORMS_ORDER.filter((m) => allowed.has(m.type));
}
const BY_TYPE = Object.fromEntries(
  STATION_BLOCK_FORMS_ORDER.map((m) => [m.type, m]),
) as Record<StationBlockType, StationBlockFormsMeta>;
export function formsLabelForStationBlockType(t: StationBlockType): string {
  return BY_TYPE[t]?.formsLabel ?? t;
}
export function formsMetaForStationBlockType(
  t: StationBlockType,
): StationBlockFormsMeta {
  return BY_TYPE[t] ?? STATION_BLOCK_FORMS_ORDER[0];
}
