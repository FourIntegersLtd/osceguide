/** The set-up request the public organisation form files for staff (H-1). */

export type SetupRequestInput = {
  name: string;
  orgType: string;
  exams: string[];
  /** Already worded for a person to read, e.g. "Recruitment". */
  purposes: string[];
  ownerName: string;
  email: string;
};

/** The `POST /site/messages` body: a contact message staff read in the console inbox. */
export function setupRequestBody(input: SetupRequestInput) {
  return {
    kind: "contact",
    name: input.ownerName,
    email: input.email,
    subject: `Set up an organisation: ${input.name}`,
    source: "register/organisation",
    body: [
      `Organisation: ${input.name}`,
      `Type: ${input.orgType}`,
      `Exams: ${input.exams.length ? input.exams.join(", ") : "none chosen"}`,
      `Use: ${input.purposes.join(", ")}`,
      `Contact: ${input.ownerName} <${input.email}>`,
    ].join("\n"),
  };
}
