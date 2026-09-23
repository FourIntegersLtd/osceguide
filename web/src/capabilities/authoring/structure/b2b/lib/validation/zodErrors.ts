import type { ZodError } from "zod"; /** First human-readable message from a Zod error (flattened field errors preferred). */
export function zodErrorFirstMessage(error: ZodError): string {
  const flat = error.flatten();
  const field = flat.fieldErrors;
  for (const key of Object.keys(field)) {
    const msgs = field[key as keyof typeof field];
    if (msgs?.[0]) return msgs[0];
  }
  const form = flat.formErrors;
  if (form[0]) return form[0];
  return error.message || "Validation failed.";
}
