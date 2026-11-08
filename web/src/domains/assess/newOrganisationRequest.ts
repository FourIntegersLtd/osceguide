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

export type EmployerRequestInput = {
  name: string;
  ownerName: string;
  email: string;
  /** "How many candidates a year?", as typed; left out when blank. */
  candidatesPerYear?: string;
};

/** The employer path files the same staff message, typed Employer, for Recruitment, with the volume as its note. */
export function employerRequestBody(input: EmployerRequestInput) {
  const volume = input.candidatesPerYear?.trim();
  return setupRequestBody({
    name: input.name,
    orgType: "Employer",
    purposes: ["Recruitment"],
    ownerName: input.ownerName,
    email: input.email,
    notes: volume ? `Candidates a year: ${volume}` : undefined,
  });
}

/** The employer path's words (board HireRegister): the form, the confirmation and the failure. */
export const EMPLOYER_REGISTER = {
  title: "Set up your employer account",
  subtitle: "Tell us who you are. We set the account up and email you within one working day.",
  hint: "Employers assess candidates for a role. Your screens say Candidate and Assessment.",
  send: "Send request",
  failed: { title: "That did not send", body: "Check your connection and press Send request again. Nothing was saved." },
  sent: (org: string, email: string) => ({
    title: "Request sent",
    heading: "We will email you",
    body: `We have your request for ${org}. Look for an email to ${email} within one working day; it has a link to finish setting up.`,
    link: "See what your account looks like",
  }),
} as const;

export type RegisterPath = "school" | "employer";
export const REGISTER_PATHS: readonly { id: RegisterPath; label: string }[] = [
  { id: "school", label: "A school or deanery" },
  { id: "employer", label: "An employer" },
];
