import type { ComponentType } from "react";
import {
  HiOutlineAcademicCap,
  HiOutlineBeaker,
  HiOutlineChatBubbleBottomCenterText,
  HiOutlineClipboardDocumentList,
  HiOutlineEyeSlash,
  HiOutlineHeart,
  HiOutlineHome,
  HiOutlineInformationCircle,
  HiOutlineUser,
  HiOutlineUserGroup,
  HiOutlineClipboardDocumentCheck,
} from "react-icons/hi2";
import { INSTITUTION_WORDS, type AssessWords } from "@/capabilities/assess-words/vocabulary";
import type {
  StationBlock,
  StationBlockRole,
  StationSection,
  StationSectionAudience,
  StationStructure,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

type Icon = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;

export type AudienceMeta = {
  id: StationSectionAudience;
  label: string;
  /** One line under the label in the section settings. */
  description: string;
  /** The role every block in this section takes unless the author picks another. */
  defaultRole: StationBlockRole;
  icon: Icon;
};

/** The parts of a station, in the order they are read. */
const STATION_AUDIENCES: AudienceMeta[] = [
  {
    id: "patient",
    label: "Patient",
    description: "The script the simulated patient follows. The candidate does not see this.",
    defaultRole: "hidden",
    icon: HiOutlineUser,
  },
  {
    id: "candidate",
    label: "Candidate brief",
    description: "Notes the candidate reads before starting the station.",
    defaultRole: "candidate_brief",
    icon: HiOutlineClipboardDocumentList,
  },
  {
    id: "examiner",
    label: "Examiner",
    description: "Model answers and marking notes for the examiner after the station.",
    defaultRole: "examiner",
    icon: HiOutlineAcademicCap,
  },
  {
    id: "faculty",
    label: "Faculty",
    description:
      "Setup, debrief and teaching notes for the people running the station. Never shown to the learner or used by the AI.",
    defaultRole: "faculty",
    icon: HiOutlineInformationCircle,
  },
];

export type RoleMeta = {
  id: StationBlockRole;
  audience: StationSectionAudience;
  label: string;
  /** How the engine uses it — shown next to the role picker. */
  description: string;
  icon: Icon;
};

export const STATION_BLOCK_ROLES: RoleMeta[] = [
  {
    id: "persona",
    audience: "patient",
    label: "Who the patient is",
    description: "Read at the top of the patient's script: identity, background, manner.",
    icon: HiOutlineUser,
  },
  {
    id: "complaint",
    audience: "patient",
    label: "Presenting complaint",
    description: "What the patient says first when asked why they came.",
    icon: HiOutlineChatBubbleBottomCenterText,
  },
  {
    id: "history",
    audience: "patient",
    label: "Medical history",
    description: "Told only when the doctor asks about it.",
    icon: HiOutlineHeart,
  },
  {
    id: "medications",
    audience: "patient",
    label: "Medications",
    description: "Told only when the doctor asks about medicines or allergies.",
    icon: HiOutlineBeaker,
  },
  {
    id: "social",
    audience: "patient",
    label: "Family and social",
    description: "Told only when the doctor asks about home, work or family.",
    icon: HiOutlineHome,
  },
  {
    id: "examination",
    audience: "patient",
    label: "Examination findings",
    description: "Revealed only if the doctor examines or asks for findings.",
    icon: HiOutlineUserGroup,
  },
  {
    id: "hidden",
    audience: "patient",
    label: "Held back until asked",
    description: "What the patient thinks, worries about, and might ask, brought up only when the doctor asks.",
    icon: HiOutlineEyeSlash,
  },
  {
    id: "instructions",
    audience: "patient",
    label: "Acting instructions",
    description: "Special instructions for how to play the station. Never spoken aloud.",
    icon: HiOutlineInformationCircle,
  },
  {
    id: "candidate_brief",
    audience: "candidate",
    label: "Candidate brief",
    description: "Shown to the candidate before the station; the patient knows it was said.",
    icon: HiOutlineClipboardDocumentList,
  },
  {
    id: "examiner",
    audience: "examiner",
    label: "Examiner notes",
    description: "Expected answers and marking points. Not shown to the patient.",
    icon: HiOutlineClipboardDocumentCheck,
  },
  {
    id: "faculty",
    audience: "faculty",
    label: "Faculty notes",
    description: "For the people running the station. The patient, the marker and the learner never get it.",
    icon: HiOutlineInformationCircle,
  },
  {
    id: "debrief",
    audience: "faculty",
    label: "Debrief guide",
    description: "Debriefing and teaching points. The AI debrief tutor works through them; the learner never sees them.",
    icon: HiOutlineInformationCircle,
  },
];

const ROLE_BY_ID = Object.fromEntries(STATION_BLOCK_ROLES.map((r) => [r.id, r])) as Record<
  StationBlockRole,
  RoleMeta
>;
const AUDIENCE_BY_ID = Object.fromEntries(STATION_AUDIENCES.map((a) => [a.id, a])) as Record<
  StationSectionAudience,
  AudienceMeta
>;

/** A label or sentence in the workspace's words: examiner -> assessor for an employer, learner -> candidate. */
function inWords(text: string, w: AssessWords): string {
  const examined = text.replace(/Examiner/g, w.Examiner).replace(/examiner/g, w.examiner);
  return w.hiring ? examined.replace(/learner/g, w.trainee) : examined;
}

function localised<T extends { label: string; description: string }>(meta: T, w: AssessWords): T {
  return { ...meta, label: inWords(meta.label, w), description: inWords(meta.description, w) };
}

export function roleMeta(role: StationBlockRole, w: AssessWords = INSTITUTION_WORDS): RoleMeta {
  return localised(ROLE_BY_ID[role] ?? ROLE_BY_ID.hidden, w);
}

/** An employer's chips say who sees a section: the candidate, or only the assessor. */
const HIRE_AUDIENCE_LABEL: Partial<Record<StationSectionAudience, string>> = { candidate: "Candidate sees it", examiner: "Assessor only" };

function audienceIn(meta: AudienceMeta, w: AssessWords): AudienceMeta {
  const named = localised(meta, w);
  const chip = w.hiring ? HIRE_AUDIENCE_LABEL[meta.id] : undefined;
  return chip ? { ...named, label: chip } : named;
}

export function audienceMeta(audience: StationSectionAudience, w: AssessWords = INSTITUTION_WORDS): AudienceMeta {
  return audienceIn(AUDIENCE_BY_ID[audience] ?? AUDIENCE_BY_ID.patient, w);
}

/** The parts of a station in reading order, named in the workspace's words. */
export function stationAudiences(w: AssessWords = INSTITUTION_WORDS): AudienceMeta[] {
  return STATION_AUDIENCES.map((a) => audienceIn(a, w));
}

export function rolesForAudience(audience: StationSectionAudience, w: AssessWords = INSTITUTION_WORDS): RoleMeta[] {
  return STATION_BLOCK_ROLES.filter((r) => r.audience === audience).map((r) => localised(r, w));
}

/** Block ids the legacy presets and seeded templates used, so an old template gets the right roles. */
const LEGACY_ROLE_BY_ID: Record<string, StationBlockRole> = {
  patient_biodata: "persona",
  gender: "persona",
  persona: "persona",
  opening_sentence: "complaint",
  expanded_history: "history",
  past_med_history_allergies: "history",
  family_social_history: "social",
  examination_findings: "examination",
  idea: "hidden",
  concerns: "hidden",
  expectation: "hidden",
  questions: "hidden",
};

const LEGACY_AUDIENCE_BY_SECTION: Record<string, StationSectionAudience> = {
  sec_patient: "patient",
  sec_candidate_brief: "candidate",
  sec_clinician_pack: "candidate",
  sec_doctor_reference: "candidate",
  sec_case: "candidate",
  sec_management: "examiner",
  sec_consultation_plan: "examiner",
  sec_workup: "examiner",
  sec_interview: "examiner",
  sec_references: "examiner",
};

export function sectionAudience(section: StationSection): StationSectionAudience {
  if (section.audience) return section.audience;
  const legacy = LEGACY_AUDIENCE_BY_SECTION[section.id];
  if (legacy) return legacy;
  const byRole = section.blocks.find((b) => b.role)?.role;
  if (byRole) return roleMeta(byRole).audience;
  if (section.blocks.some((b) => LEGACY_ROLE_BY_ID[b.id])) return "patient";
  return "patient";
}

export function blockRole(block: StationBlock, section: StationSection): StationBlockRole {
  if (block.role) return block.role;
  const audience = sectionAudience(section);
  if (audience === "patient") return LEGACY_ROLE_BY_ID[block.id] ?? "hidden";
  return audienceMeta(audience).defaultRole;
}

/**
 * The structure as platform-api's renderer reads it: the editor's `sections`
 * untouched, plus a flat ordered `blocks` list carrying each block's role and
 * the template-level `layout`. platform-api stores the document whole, so the
 * editor round-trips through `sections` and the engine reads `blocks`.
 */
export function toPlatformStructure(structure: StationStructure): StationStructure & {
  blocks: Array<{ id: string; label: string; kind: "text" | "list"; role: StationBlockRole }>;
  layout: { persona: "patient" | "examiner"; greeting?: string };
} {
  const blocks = structure.sections.flatMap((section) =>
    section.blocks.map((block) => ({
      id: block.id,
      label: block.label,
      kind: (block.type === "list" || block.type === "multiSelect" || block.type === "checklist"
        ? "list"
        : "text") as "text" | "list",
      role: blockRole(block, section),
    })),
  );
  const greeting = structure.layout?.greeting?.trim();
  return {
    ...structure,
    blocks,
    layout: { persona: structure.layout?.persona ?? "patient", ...(greeting ? { greeting } : {}) },
  };
}
