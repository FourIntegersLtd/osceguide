import type { B2CReadingToneKey } from "@/foundation/ui/productTokens";
import { asText, humanise, type AudienceBlock, type AudienceSection } from "./sectionsByAudience";

/**
 * How one block of the model answer is presented: the card heading and tone
 * the legacy b2c `ManagementScreen` gave it, and the group it sat in. Keyed by
 * the template's block id — presentation follows the template's own
 * vocabulary, never an exam code. `group: null` is a card above every group.
 */
type ManagementBlockMeta = {
  title?: string;
  tone: B2CReadingToneKey;
  group: string | null;
};

const CLINICAL_ASSESSMENT = "Clinical Assessment";
const SOCIAL_AND_CONCERNS = "Social & Patient Concerns";
const TREATMENT_AND_ACTIONS = "Treatment & Actions";
const EDUCATION_AND_FOLLOW_UP = "Patient Education & Follow-up";
const ADDITIONAL_NOTES = "Additional Notes";

/** The legacy groups in their legacy order; a template's own groups follow these. */
const LEGACY_GROUP_ORDER = [
  CLINICAL_ASSESSMENT,
  SOCIAL_AND_CONCERNS,
  TREATMENT_AND_ACTIONS,
  EDUCATION_AND_FOLLOW_UP,
  ADDITIONAL_NOTES,
];

const MANAGEMENT_BLOCK_META: Record<string, ManagementBlockMeta> = {
  explanation: { tone: "education", group: null },
  description: { tone: "education", group: null },
  differential_diagnosis: { tone: "reasoning", group: CLINICAL_ASSESSMENT },
  diagnostic_criteria: { tone: "reasoning", group: CLINICAL_ASSESSMENT },
  assessment: { title: "Assessment Steps", tone: "reasoning", group: CLINICAL_ASSESSMENT },
  management_examination_findings: { title: "Examination Findings", tone: "examination", group: CLINICAL_ASSESSMENT },
  further_investigations: { tone: "examination", group: CLINICAL_ASSESSMENT },
  risk_factors: { tone: "safety", group: CLINICAL_ASSESSMENT },
  social_concerns: { tone: "history", group: SOCIAL_AND_CONCERNS },
  ice: { title: "ICE Response", tone: "history", group: SOCIAL_AND_CONCERNS },
  immediate_actions: { tone: "safety", group: TREATMENT_AND_ACTIONS },
  pharmacological_treatment: { title: "Medications", tone: "management", group: TREATMENT_AND_ACTIONS },
  non_pharmacological_treatment: { tone: "management", group: TREATMENT_AND_ACTIONS },
  psychological_treatment: { tone: "management", group: TREATMENT_AND_ACTIONS },
  social_interventions: { tone: "management", group: TREATMENT_AND_ACTIONS },
  health_education: { tone: "education", group: EDUCATION_AND_FOLLOW_UP },
  follow_up: { tone: "safety", group: EDUCATION_AND_FOLLOW_UP },
  safety_netting: { tone: "safety", group: EDUCATION_AND_FOLLOW_UP },
  safety_planning: { tone: "safety", group: EDUCATION_AND_FOLLOW_UP },
  additional_notes: { tone: "education", group: ADDITIONAL_NOTES },
  specialties: { tone: "education", group: ADDITIONAL_NOTES },
};

/** Tones for blocks the map does not know: positional, only to separate neighbouring cards. */
const UNKNOWN_BLOCK_TONES: readonly B2CReadingToneKey[] = [
  "reasoning",
  "examination",
  "management",
  "history",
  "education",
  "safety",
];

export type ManagementEntry = {
  block: AudienceBlock;
  title: string;
  tone: B2CReadingToneKey;
};

export type ManagementGroup = {
  title: string;
  /** The first legacy group reads open under a heading; the rest are collapsible panels. */
  collapsible: boolean;
  entries: ManagementEntry[];
};

export type ManagementLayout = {
  /** Cards above every group: the explanation the legacy screen led with. */
  lead: ManagementEntry[];
  groups: ManagementGroup[];
};

function hasContent(block: AudienceBlock): boolean {
  return asText(block.value) !== "";
}

/**
 * The model answer's blocks, arranged as the legacy management screen had
 * them: the explanation first, "Clinical Assessment" open, then one
 * collapsible group per stage. A block the map does not know is grouped under
 * its own template section's title, after the legacy groups, so a new exam's
 * template still reads as sections of cards. Empty blocks are left out.
 */
export function managementLayout(sections: AudienceSection[]): ManagementLayout {
  const lead: ManagementEntry[] = [];
  const entriesByGroup = new Map<string, ManagementEntry[]>();
  let unknownBlockCount = 0;

  for (const section of sections) {
    for (const block of section.blocks) {
      if (!hasContent(block)) continue;
      const meta = MANAGEMENT_BLOCK_META[block.id];
      const entry: ManagementEntry = {
        block,
        title: meta?.title ?? (block.label || humanise(block.id)),
        tone: meta?.tone ?? UNKNOWN_BLOCK_TONES[unknownBlockCount++ % UNKNOWN_BLOCK_TONES.length]!,
      };
      if (meta && meta.group === null) {
        lead.push(entry);
        continue;
      }
      const groupTitle = meta?.group ?? section.title;
      entriesByGroup.set(groupTitle, [...(entriesByGroup.get(groupTitle) ?? []), entry]);
    }
  }

  const templateGroups = [...entriesByGroup.keys()].filter((title) => !LEGACY_GROUP_ORDER.includes(title));
  const groups = [...LEGACY_GROUP_ORDER, ...templateGroups].flatMap((title): ManagementGroup[] => {
    const entries = entriesByGroup.get(title);
    return entries ? [{ title, collapsible: title !== CLINICAL_ASSESSMENT, entries }] : [];
  });
  return { lead, groups };
}
