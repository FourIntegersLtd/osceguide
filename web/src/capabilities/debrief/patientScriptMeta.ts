import type { IconType } from "react-icons";
import {
  HiOutlineBookOpen,
  HiOutlineChatBubbleLeftEllipsis,
  HiOutlineClipboardDocumentList,
  HiOutlineExclamationTriangle,
  HiOutlineHandRaised,
  HiOutlineLightBulb,
  HiOutlineNewspaper,
  HiOutlineQuestionMarkCircle,
  HiOutlineUser,
  HiOutlineUsers,
} from "react-icons/hi2";
import type { B2CSectionIconTone } from "@/foundation/ui";
import {
  asText,
  humanise,
  type AudienceBlock,
  type AudienceSection,
} from "@/capabilities/attempt-runner/material/sectionsByAudience";

/** The three tabs of the legacy b2c `PatientPreparation` script. */
export type PatientScriptTab = "history" | "ice" | "persona";

/** How a block's content is drawn inside its section. */
export type PatientScriptStyle = "quote" | "bullets" | "questions";

/**
 * How one block of the patient's script is presented: the tab it sat on in
 * the legacy screen, its heading, icon and badge tone. Keyed by the
 * template's block id — never by an exam code.
 */
type PatientScriptBlockMeta = {
  tab: PatientScriptTab;
  title: string;
  icon: IconType;
  tone: B2CSectionIconTone;
  style: PatientScriptStyle;
};

const PATIENT_SCRIPT_BLOCK_META: Record<string, PatientScriptBlockMeta> = {
  opening_sentence: { tab: "history", title: "Your opening sentence", icon: HiOutlineChatBubbleLeftEllipsis, tone: "primary", style: "quote" },
  expanded_history: { tab: "history", title: "The story (details to give if asked)", icon: HiOutlineBookOpen, tone: "sky", style: "bullets" },
  family_social_history: { tab: "history", title: "Background", icon: HiOutlineUsers, tone: "emerald", style: "bullets" },
  past_med_history_allergies: { tab: "history", title: "Medical history", icon: HiOutlineNewspaper, tone: "rose", style: "bullets" },
  idea: { tab: "ice", title: "Ideas", icon: HiOutlineLightBulb, tone: "amber", style: "bullets" },
  concerns: { tab: "ice", title: "Concerns", icon: HiOutlineExclamationTriangle, tone: "rose", style: "bullets" },
  expectation: { tab: "ice", title: "Expectations", icon: HiOutlineHandRaised, tone: "violet", style: "bullets" },
  questions: { tab: "ice", title: "Questions you may ask", icon: HiOutlineQuestionMarkCircle, tone: "orange", style: "questions" },
  persona: { tab: "persona", title: "Your personality & approach", icon: HiOutlineUser, tone: "primary", style: "bullets" },
};

/** Blocks the legacy script showed in its header line, not as a section. */
const HEADER_ONLY_BLOCKS = new Set(["patient_biodata", "gender"]);

export type PatientScriptEntry = {
  block: AudienceBlock;
  title: string;
  icon: IconType;
  tone: B2CSectionIconTone;
  style: PatientScriptStyle;
};

/**
 * The patient's blocks sorted onto the legacy tabs. A block the map does not
 * know joins the History tab under its own label, so a new template's script
 * still shows in full. Empty blocks are left out.
 */
export function patientScriptTabs(sections: AudienceSection[]): Record<PatientScriptTab, PatientScriptEntry[]> {
  const tabs: Record<PatientScriptTab, PatientScriptEntry[]> = { history: [], ice: [], persona: [] };
  for (const section of sections) {
    for (const block of section.blocks) {
      if (HEADER_ONLY_BLOCKS.has(block.id) || asText(block.value) === "") continue;
      const meta = PATIENT_SCRIPT_BLOCK_META[block.id];
      tabs[meta?.tab ?? "history"].push({
        block,
        title: meta?.title ?? (block.label || humanise(block.id)),
        icon: meta?.icon ?? HiOutlineClipboardDocumentList,
        tone: meta?.tone ?? "primary",
        style: meta?.style ?? "bullets",
      });
    }
  }
  return tabs;
}

/** A block's value as lines: a list's items, or a text's non-empty lines. */
export function scriptLines(value: unknown): string[] {
  const parts = Array.isArray(value) ? value.map(asText) : asText(value).split("\n");
  return parts.map((line) => line.trim()).filter((line) => line !== "");
}
