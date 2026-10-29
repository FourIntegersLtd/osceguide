/** The set-up request the public organisation form files for staff (H-1). */

export type SetupRequestInput = {
  name: string;
  orgType: string;
  /** Already worded for a person to read, e.g. "Recruitment". */
  purposes: string[];
  ownerName: string;
  email: string;
  /** Free text from the form; left out of the message when blank. */
  notes?: string;
};

/** The `POST /site/messages` body: a contact message staff read in the console inbox. */
export function setupRequestBody(input: SetupRequestInput) {
  const notes = input.notes?.trim();
  return {
    kind: "contact",
    name: input.ownerName,
    email: input.email,
    subject: `Set up an organisation: ${input.name}`,
    source: "register/organisation",
    body: [
      `Organisation: ${input.name}`,
      `Type: ${input.orgType}`,
      `Use: ${input.purposes.join(", ")}`,
      `Contact: ${input.ownerName} <${input.email}>`,
      ...(notes ? [`Notes: ${notes}`] : []),
    ].join("\n"),
  };
}
