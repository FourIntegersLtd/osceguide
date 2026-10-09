import type { IconType } from "react-icons";
import {
  HiOutlineBeaker,
  HiOutlineCamera,
  HiOutlineChatBubbleLeftRight,
  HiOutlineClipboardDocumentList,
  HiOutlineHeart,
  HiOutlineIdentification,
  HiOutlineNewspaper,
  HiOutlineUser,
  HiOutlineUserCircle,
  HiOutlineUsers,
  HiOutlineViewfinderCircle,
} from "react-icons/hi2";
import type { B2CSectionIconTone } from "@/foundation/ui";
import { humanise, type AudienceSection } from "./sectionsByAudience";

/**
 * How one block of the candidate's brief is presented: the heading, icon and
 * badge tone the legacy b2c reading phase gave it, and where in the reading
 * order it sat. Keyed by the template's block id — presentation follows the
 * template's own vocabulary, never an exam code.
 */
export type BriefBlockMeta = {
  title?: string;
  icon: IconType;
  tone: B2CSectionIconTone;
  /** Legacy reading order within the brief; unlisted blocks keep template order after these. */
  order?: number;
};

/**
 * The legacy b2c doctor screens, block by block. SCA's ScaDoctorScreen put
 * photos first then biodata, notes, medications, history, social, and
 * investigations; PLAB and CASC renamed their task blocks "Your Role" /
 * "Your Task"; Ortho's screens gave the scenario, radiograph, images and
 * patient list their own icons.
 */
const BRIEF_BLOCK_META: Record<string, BriefBlockMeta> = {
  // SCA — ScaDoctorScreen
  doctor_photos: { title: "Photos", icon: HiOutlineCamera, tone: "sky", order: 0 },
  doctor_patient_biodata: { title: "Patient Biodata", icon: HiOutlineIdentification, tone: "primary", order: 1 },
  recent_notes: { title: "Recent Notes", icon: HiOutlineNewspaper, tone: "emerald", order: 2 },
  current_medications: { title: "Current Medications", icon: HiOutlineClipboardDocumentList, tone: "violet", order: 3 },
  past_medical_history: { title: "Past Medical History", icon: HiOutlineHeart, tone: "rose", order: 4 },
  social_history: { title: "Social History", icon: HiOutlineUsers, tone: "amber", order: 5 },
  recent_investigations: { title: "Recent Investigations", icon: HiOutlineBeaker, tone: "sky", order: 6 },
  // PLAB 2 — PlabDoctorScreen
  doctor_identity: { title: "Your Role", icon: HiOutlineUserCircle, tone: "primary", order: 1 },
  patient_information: { title: "Patient Information", icon: HiOutlineUser, tone: "emerald", order: 2 },
  task_instructions: { title: "Your Task", icon: HiOutlineClipboardDocumentList, tone: "amber", order: 3 },
  // CASC — CascDoctorScreen
  doctor_task: { title: "Your Role", icon: HiOutlineUserCircle, tone: "primary", order: 1 },
  // Ortho ST3 — OrthoDoctorScreen
  clinical_scenario: { title: "Clinical Scenario", icon: HiOutlineClipboardDocumentList, tone: "primary", order: 1 },
  radiograph_image_url: { title: "Images", icon: HiOutlineViewfinderCircle, tone: "sky", order: 2 },
  patient_list_for_candidate: { title: "Patient List", icon: HiOutlineUsers, tone: "emerald", order: 3 },
  background_overview: { title: "Background", icon: HiOutlineChatBubbleLeftRight, tone: "violet", order: 4 },
};

/** A block a template this map does not know: quiet clipboard, template order. */
const FALLBACK_META: BriefBlockMeta = { icon: HiOutlineClipboardDocumentList, tone: "primary" };

/** Meta after the last legacy-ordered block, so unknown blocks trail in template order. */
const UNLISTED_ORDER = 100;

export type BriefBlockEntry = {
  block: AudienceSection["blocks"][number];
  title: string;
  icon: IconType;
  tone: B2CSectionIconTone;
};

/**
 * The brief's blocks flattened across sections and put in the legacy reading
 * order, each carrying the heading, icon and tone its subsection is drawn
 * with. A block the map does not know keeps its own label and template
 * position, after the known ones.
 */
export function briefBlockEntries(sections: AudienceSection[]): BriefBlockEntry[] {
  const flattened = sections.flatMap((section) => section.blocks);
  return flattened
    .map((block, index) => {
      const meta = BRIEF_BLOCK_META[block.id] ?? FALLBACK_META;
      return {
        entry: {
          block,
          title: meta.title ?? (block.label || humanise(block.id)),
          icon: meta.icon,
          tone: meta.tone,
        },
        rank: meta.order ?? UNLISTED_ORDER + index,
        index,
      };
    })
    .sort((a, b) => a.rank - b.rank || a.index - b.index)
    .map(({ entry }) => entry);
}
