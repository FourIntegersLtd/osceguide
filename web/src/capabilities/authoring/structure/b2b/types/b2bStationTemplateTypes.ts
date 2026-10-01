export type StationBlockType =
  | "shortText"
  | "longText"
  | "list"
  | "singleSelect"
  | "multiSelect"
  | "checklist"
  | "scale"
  | "ragCriterion"
  | "media"
  | "records"
  | "qaList"
  | "groupedList";

/** One column of a `records` block: the key in each record, and its heading. */
export type RecordField = { key: string; label: string };

/**
 * What a block is *for*. Mirrors `KNOWN_ROLES` in the assessment engine's
 * station prompt formatter: the renderer places a block by its role, so the
 * patient never volunteers the model answer and the examiner's notes never
 * reach the candidate. Widget type says how an author types it in; role says
 * who reads it and when.
 */
export type StationBlockRole =
  | "persona"
  | "complaint"
  | "history"
  | "medications"
  | "social"
  | "examination"
  | "instructions"
  | "hidden"
  | "candidate_brief"
  | "examiner"
  | "faculty";

/**
 * Who a section is written for: the three classic parts of a station, and the
 * faculty running it. Faculty material is never read to the patient, the
 * marker or the learner.
 */
export type StationSectionAudience = "patient" | "candidate" | "examiner" | "faculty";

/** LLM autogenerate settings stored on the template version structure. */
export type StationStructureGeneration = {
  profileKey: string;
  systemPromptAppend?: string;
  /** Org templates only; requires profileKey `custom`. */
  systemPromptOverride?: string;
};

export type StationBlockBase = {
  id: string;
  type: StationBlockType;
  label: string;
  role?: StationBlockRole;
  required?: boolean;
  placeholder?: string;
  /** LLM-only hint for Generate draft; separate from author placeholder. */
  generationHint?: string;
  /** @deprecated Nothing reads this at runtime; kept so stored templates parse. */
  readingBrief?: boolean;
};
export type StationBlock =
  | (StationBlockBase & { type: "shortText" })
  | (StationBlockBase & { type: "longText" })
  | (StationBlockBase & { type: "list"; itemLabel?: string })
  | (StationBlockBase & { type: "singleSelect"; options: string[] })
  | (StationBlockBase & { type: "multiSelect"; options: string[] })
  | (StationBlockBase & {
      type: "checklist";
      items: Array<{ id: string; label: string }>;
    })
  | (StationBlockBase & {
      type: "scale";
      min: number;
      max: number;
      labels?: Record<string, string>;
    })
  | (StationBlockBase & {
      type: "ragCriterion";
      /** B2C-aligned path stem, e.g. `global_skills.structures_consultation` */
      pathStem: string;
    })
  | (StationBlockBase & { type: "media" })
  | (StationBlockBase & { type: "records"; fields?: RecordField[] })
  | (StationBlockBase & { type: "qaList" })
  | (StationBlockBase & { type: "groupedList" });
export type StationSection = {
  id: string;
  title: string;
  description?: string;
  audience?: StationSectionAudience;
  /** @deprecated Nothing reads this at runtime; kept so stored templates parse. */
  readingBriefDefault?: boolean;
  blocks: StationBlock[];
};
/** Template-level presentation: who the AI plays and how it opens. */
export type StationStructureLayout = {
  persona?: "patient" | "examiner";
  greeting?: string;
};
export type StationStructure = {
  schemaVersion: 1;
  sections: StationSection[];
  layout?: StationStructureLayout;
  generation?: StationStructureGeneration;
};
export type StationTemplateStartPoint =
  | "blank"
  | "asterix"
  | "sca"
  | "plab"
  | "casc"
  | "ortho"
  | "ortho_prioritisation"
  | "ortho_communication"
  | "ortho_portfolio";
