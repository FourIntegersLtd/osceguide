import type { StationBlock, StationSection, StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

/**
 * The AI patient's script, shared by every consultation preset. Five short
 * sections, one per role the engine reads: who they are, what they open with,
 * what they reveal when asked, home and family, and what they hold back.
 * Block ids are the ones the generation hints and the legacy models use.
 */
export function patientScriptSections(extraHistory: StationBlock[] = []): StationSection[] {
  const sections: StationSection[] = [
    {
      id: "sec_patient_identity",
      title: "Who the patient is",
      audience: "patient",
      description: "Read at the top of the script: identity and manner.",
      blocks: [
      {
        id: "patient_biodata",
        type: "shortText",
        role: "persona",
        label: "Patient Biodata",
        required: true,
        placeholder:
          "e.g. Aisha Khan, 24, female, university student",
      },
      {
        id: "gender",
        type: "singleSelect",
        role: "persona",
        label: "Gender",
        required: true,
        options: ["male", "female"],
      },
      {
        id: "persona",
        type: "longText",
        role: "persona",
        label: "Persona",
        placeholder:
          "Tone, anxiety level, how they open up. e.g. Nervous at first but cooperative; tearful when discussing family.",
      },
      ],
    },
    {
      id: "sec_patient_complaint",
      title: "Presenting complaint",
      audience: "patient",
      description: "What the patient says first when asked why they came.",
      blocks: [
      {
        id: "opening_sentence",
        type: "longText",
        role: "complaint",
        label: "Opening sentence",
        required: true,
        placeholder:
          "First-person line the AI patient says to open (no “Hi doctor”). e.g. I'm pregnant… I need an abortion. If my family finds out, I'm scared they'll kill me.",
      },
      ],
    },
    {
      id: "sec_patient_history",
      title: "History",
      audience: "patient",
      description: "Told only when the doctor asks.",
      blocks: [
      {
        id: "expanded_history",
        type: "longText",
        role: "history",
        label: "Expanded history",
        required: true,
        placeholder:
          "Full history the patient reveals when asked — not the opening line.",
      },
      {
        id: "past_med_history_allergies",
        type: "list",
        role: "history",
        label: "Past medical history and allergies",
      },
      ],
    },
    {
      id: "sec_patient_social",
      title: "Family and social",
      audience: "patient",
      description: "Told only when the doctor asks about home, work or family.",
      blocks: [
      {
        id: "family_social_history",
        type: "list",
        role: "social",
        label: "Family and social history",
      },
      ],
    },
    {
      id: "sec_patient_hidden",
      title: "Held back until asked",
      audience: "patient",
      description: "Surfaced only when the doctor draws them out.",
      blocks: [
      {
        id: "idea",
        type: "list",
        role: "hidden",
        label: "Ideas (ICE)",
      },
      {
        id: "concerns",
        type: "list",
        role: "hidden",
        label: "Concerns (ICE)",
      },
      {
        id: "expectation",
        type: "list",
        role: "hidden",
        label: "Expectations (ICE)",
      },
      {
        id: "questions",
        type: "list",
        role: "hidden",
        label: "Questions the patient may ask",
      },
      ],
    },
  ];
  const history = sections[2];
  if (history && extraHistory.length) history.blocks = [...history.blocks, ...extraHistory];
  return sections;
}

export function consultationStructure(sections: StationSection[]): StationStructure {
  return { schemaVersion: 1, layout: { persona: "patient" }, sections };
}
