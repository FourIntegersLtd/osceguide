import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

/** The Settings two-step card's words: staff in an institution, administrators and assessors for an employer. */
export function staffMfaCopy(required: boolean, w: AssessWords): { title: string; detail: string } {
  const who = w.hiring ? `Administrators and ${w.supervisors}` : "Staff";
  return {
    title: w.hiring ? "Two-step sign-in" : "Two-step sign-in for staff",
    detail: required
      ? w.hiring
        ? `${who} must also enter a code from their phone when they sign in.`
        : "Staff must confirm a code as well as a password."
      : `${who} sign in with a password alone.`,
  };
}

/** The two-step choice as the board's pill pair; `on` marks the policy the organisation has now. */
export function mfaPills(required: boolean): { label: string; on: boolean }[] {
  return [
    { label: "Optional", on: !required },
    { label: "Required for administrators and assessors", on: required },
  ];
}

export const MFA_PILLS_HINT = "Anyone without it set up is asked to add it the next time they sign in.";
export const MFA_PILLS_CHANGE = "Our team changes this with you. Contact support to switch it.";

/** The Single sign-on card's lead. */
export function ssoLead(w: AssessWords): string {
  return w.hiring
    ? "Staff sign in with their work account when single sign-on is connected. Candidates still sign in with email."
    : "OSCE Guide sets this up with you. Contact support to change it.";
}
