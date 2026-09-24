/**
 * The specialty tags a question can carry.
 *
 * Mirrors the retiring client's `MEDICAL_SPECIALTIES_CATEGORIES`
 * (`frontend/src/b2c/config/constants/constants.ts`) key-for-key, because the
 * stored tag *is* the key: the backend normalises to lowercase and the feed
 * filter matches on it, so a key that drifted would silently orphan every
 * question already tagged with the old spelling. The colour each entry carried
 * there is dropped — the chip row styles from the product tokens, not per-tag
 * colours, exactly as the old community chips did.
 */
export interface SpecialtyTag {
  /** What is stored and filtered on. Lowercase snake_case. */
  key: string;
  /** What the chip says. */
  name: string;
}

export const MEDICAL_SPECIALTIES_CATEGORIES: readonly SpecialtyTag[] = [
  { name: "Internal Medicine", key: "internal_medicine" },
  { name: "Acute Medicine", key: "acute_medicine" },
  { name: "Emergency Medicine", key: "emergency_medicine" },
  { name: "Cardiology", key: "cardiology" },
  { name: "Respiratory", key: "respiratory" },
  { name: "Gastroenterology", key: "gastroenterology" },
  { name: "Nephrology", key: "nephrology" },
  { name: "Neurology", key: "neurology" },
  { name: "Endocrinology", key: "endocrinology" },
  { name: "Ophthalmology", key: "ophthalmology" },
  { name: "ENT", key: "ent" },
  { name: "Dermatology", key: "dermatology" },
  { name: "Rheumatology", key: "rheumatology" },
  { name: "Musculoskeletal", key: "musculoskeletal" },
  { name: "Orthopedics", key: "orthopedics" },
  { name: "General Surgery", key: "general_surgery" },
  { name: "Urology", key: "urology" },
  { name: "Vascular Surgery", key: "vascular_surgery" },
  { name: "Paediatrics", key: "paediatrics" },
  { name: "Geriatrics", key: "geriatrics" },
  { name: "Obs and Gyne", key: "obs_and_gyne" },
  { name: "Psychiatry", key: "psychiatry" },
  { name: "Hematology", key: "hematology" },
  { name: "Oncology", key: "oncology" },
  { name: "Infectious Diseases", key: "infectious_diseases" },
  { name: "Palliative Care", key: "palliative_care" },
  { name: "Chronic Conditions", key: "chronic_conditions" },
  { name: "Preventive Medicine", key: "preventive_medicine" },
  { name: "Miscellaneous", key: "miscellaneous" },
];

/** The chips in the order the retiring client showed them: alphabetical by name. */
export const SPECIALTY_TAGS_SORTED: readonly SpecialtyTag[] = [
  ...MEDICAL_SPECIALTIES_CATEGORIES,
].sort((a, b) => a.name.localeCompare(b.name));
