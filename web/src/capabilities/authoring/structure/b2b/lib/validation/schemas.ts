import { z } from "zod";
import { zodErrorFirstMessage } from "./zodErrors";
export const b2bOrgSlugSchema = z
  .string()
  .trim()
  .min(1, "Institution slug is required.")
  .max(80)
  .regex(
    /^[a-z0-9]+(-[a-z0-9]+)*$/,
    "Use lowercase letters, numbers, and single hyphens only.",
  );
export const b2bSignupFormSchema = z.object({
  name: z.string().trim().max(200).optional(),
  orgSlug: b2bOrgSlugSchema,
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(6, "Password must be at least 6 characters."),
});
export const b2bLoginFormSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
}); /** Manual trainee row on Team page */
export const b2bTraineeManualFormSchema = z.object({
  fullName: z.string().trim().min(1, "Enter the trainee’s full name.").max(200),
  email: z.string().trim().email("Enter a valid email address."),
  cohort: z.string().trim().max(120),
});
/** CSV upload. staff/trainee imports are CSV-only on the API today */
export const b2bTraineeUploadFilenameSchema = z
  .string()
  .min(1, "Choose a file.")
  .refine((name) => /\.csv$/i.test(name.trim()), {
    message: "Upload a .csv file.",
  }); /** Staff spreadsheet upload. CSV only (matches backend) */
export const b2bStaffUploadFilenameSchema = b2bTraineeUploadFilenameSchema;
const feedbackTemplateChoiceField = z
  .string()
  .min(1, "Choose a published feedback template.")
  .refine((v) => v !== "__none__", {
    message: "Choose a published feedback template.",
  })
  .refine(
    (v) => {
      const idx = v.lastIndexOf("|");
      if (idx <= 0) return false;
      const idPart = v.slice(0, idx).trim();
      const ver = parseInt(v.slice(idx + 1), 10);
      return idPart.length > 0 && Number.isFinite(ver) && ver > 0;
    },
    { message: "Choose a valid published feedback template." },
  );
export const b2bSessionEditFormSchema = z.object({
  sessionName: z.string().trim().min(1, "Enter a session name.").max(300),
  sessionMode: z.enum(["training", "exam"]),
  feedbackTemplateChoice: feedbackTemplateChoiceField,
});
export const b2bCircuitNameSchema = z
  .string()
  .trim()
  .min(1, "Enter a circuit name.")
  .max(200);
export const b2bSlotFeedbackFormSchema = z.object({
  notes: z.string().max(10000, "Notes are too long."),
});
export const b2bTemplateTitleSchema = z
  .string()
  .trim()
  .min(1, "Enter a template title.")
  .max(200);
export const b2bStationCreateFormSchema = z.object({
  title: z.string().trim().min(1, "Please enter a station title.").max(300),
  templateId: z.string().trim().min(1, "Please choose a published template."),
  templateVersion: z.number().int().positive(),
});
export const b2bStationAiPromptSchema = z.object({
  prompt: z
    .string()
    .trim()
    .min(10, "Enter at least a few lines for the prompt.")
    .max(20000),
}); /** Session wizard. step 1 + finalize: name, type, and required published feedback template */
export const b2bNewSessionMetaSchema = z.object({
  name: z.string().trim().min(1, "Enter a session name.").max(300),
  sessionType: z.enum(["training", "exam"]),
  feedbackTemplateChoice: feedbackTemplateChoiceField,
}); /** * Training: same count of trainees and stations per circuit. * Exam: exactly one trainee and at least one station per circuit. */
export function validateCircuitTraineeStationPairing(
  isExam: boolean,
  traineeIds: string[],
  stationIds: string[],
  options?: { effectiveTraineeCount?: number },
): string | null {
  if (isExam) {
    const effective = options?.effectiveTraineeCount ?? traineeIds.length;
    if (effective !== 1) {
      return `Exam: pick exactly one trainee per circuit (currently ${effective}).`;
    }
    if (stationIds.length < 1) {
      return `Exam: pick stations (currently ${stationIds.length}).`;
    }
  } else {
    const tCount = options?.effectiveTraineeCount ?? traineeIds.length;
    if (tCount === 0 && stationIds.length === 0) {
      return "This circuit is empty. Add trainees and stations, or remove the circuit.";
    }
    if (tCount !== stationIds.length) {
      return `Pick the same number of trainees and stations (${tCount} trainees, ${stationIds.length} stations).`;
    }
  }
  return null;
}
export function validateCircuitNameTrimmed(name: string): string | null {
  const r = b2bCircuitNameSchema.safeParse(name);
  return r.success ? null : zodErrorFirstMessage(r.error);
} /** Validates every circuit in the new-session wizard before create API call. */
export function validateNewSessionCircuits(
  sessionType: "training" | "exam",
  circuits: Array<{
    name?: string;
    traineeIds: string[];
    stationIds: string[];
  }>,
): string | null {
  if (!circuits.length) return "Add at least one circuit.";
  const isExam = sessionType === "exam";
  for (let i = 0; i < circuits.length; i++) {
    const c = circuits[i];
    if (!c) continue;
    const label = (c.name && String(c.name).trim()) || `Circuit ${i + 1}`;
    const pairErr = validateCircuitTraineeStationPairing(
      isExam,
      c.traineeIds,
      c.stationIds,
    );
    if (pairErr) return `${label}: ${pairErr}`;
  }
  return null;
}
