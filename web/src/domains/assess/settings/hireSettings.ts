import type { AssessWords } from "@/capabilities/assess-words/vocabulary";
import type { OrganizationChanges } from "@/domains/assess/api";
import { isPlatformError } from "@/foundation/platform-client";

/** The organisation's tab labels beyond Organisation: an employer's board names them Sign-in and Automatic user sync. */
export function orgTabLabels(w: AssessWords): { sso: string; provisioning: string } {
  return w.hiring
    ? { sso: "Sign-in", provisioning: "Automatic user sync" }
    : { sso: "Single sign-on", provisioning: "Provisioning" };
}

/** The Organisation card's lead. */
export function organisationLead(w: AssessWords): string {
  return w.hiring
    ? "Your organisation's web address cannot be changed here. Email support to change it."
    : "The web address is fixed. Contact support to change it.";
}

/** The Organisation form's Save button: an employer saves name and contact, an institution the name. */
export function organisationSaveLabel(w: AssessWords): string {
  return w.hiring ? "Save changes" : "Save name";
}

/** The Plan row: what the api tells us about the organisation's contract and seats, no figures it does not have. */
export function planLine(
  org: { contract_ends_at?: string | null; candidate_seats?: number | null },
  day: (iso: string) => string,
  seatsUsed?: number | null,
): string {
  const parts = ["Employer"];
  if (org.candidate_seats != null) {
    parts.push(seatsUsed != null ? `${org.candidate_seats} candidate seats, ${seatsUsed} used` : `${org.candidate_seats} candidate seats`);
  }
  if (org.contract_ends_at) parts.push(`contract runs to ${day(org.contract_ends_at)}`);
  return parts.join(" · ");
}

/** Looks like an email, or is empty (a cleared contact): the server's refusal is the truth, this only disables Save. */
export function contactEmailLooksValid(value: string): boolean {
  const text = value.trim();
  return text === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text);
}

/**
 * What the Organisation form sends: only the fields that changed. An employer may also change the
 * contact email; clearing it sends null, which the api reads as cleared (an empty string it refuses).
 * An institution's form is the name alone. Null when nothing changed.
 */
export function organisationChanges(
  org: { name: string; contact_email?: string | null },
  edited: { name: string; contactEmail: string },
  w: AssessWords,
): OrganizationChanges | null {
  const changes: OrganizationChanges = {};
  const name = edited.name.trim();
  if (name !== "" && name !== org.name) changes.name = name;
  const contact = edited.contactEmail.trim();
  if (w.hiring && contact !== (org.contact_email ?? "")) changes.contact_email = contact === "" ? null : contact;
  return Object.keys(changes).length > 0 ? changes : null;
}

const CONTACT_EMAIL_REFUSED = "That contact email does not look right. Check it and try again.";

/** Words for a failed Organisation save; the server's own sentence for anything but a refused contact email. */
export function organisationFailure(cause: unknown, changes: OrganizationChanges, fallback: (cause: unknown) => string): string {
  if (isPlatformError(cause) && cause.code === "invalid_input" && changes.contact_email) return CONTACT_EMAIL_REFUSED;
  return fallback(cause);
}
