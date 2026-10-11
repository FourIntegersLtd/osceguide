/** The subjects the Contact form offers; `other` reveals a text input. */
export const CONTACT_SUBJECTS = [
  { value: "general", label: "General enquiry" },
  { value: "information", label: "Request for information" },
  { value: "problem", label: "Problem with a station or session" },
  { value: "feedback", label: "Feedback" },
  { value: "other", label: "Other" },
] as const;

export type ContactSubject = (typeof CONTACT_SUBJECTS)[number]["value"];

/** The `subject` string sent with the message: the option's label, or the typed text for Other. Empty when incomplete. */
export function contactSubjectText(choice: ContactSubject | "", other: string): string {
  if (!choice) return "";
  if (choice === "other") return other.trim();
  return CONTACT_SUBJECTS.find((subject) => subject.value === choice)?.label ?? "";
}
