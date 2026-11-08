import type { Trainee } from "@/domains/assess/api";
import type { Cohort } from "@/domains/assess/roster/api";

export type CandidatePillKey = "all" | "invited" | { intake: string };

type CandidatePill = { key: CandidatePillKey; label: string };

/** Joined once the person has an account in use; Invited until then; removed access always shows. */
export function candidateStatus(t: Pick<Trainee, "user_id" | "invitation_pending" | "access_revoked" | "is_member">): { label: string; tone: "ok" | "warn" | "neutral" } {
  if (t.access_revoked) return { label: "Access removed", tone: "neutral" };
  if (t.user_id === null || t.invitation_pending) return { label: "Invited", tone: "warn" };
  return { label: "Joined", tone: "ok" };
}

export function isInvitedNotJoined(t: Pick<Trainee, "user_id" | "invitation_pending" | "access_revoked">): boolean {
  return !t.access_revoked && (t.user_id === null || t.invitation_pending);
}

/**
 * The pills above the list: All, one per intake, Invited not joined. Counts come from the rows loaded,
 * so they are shown only once every row is here (`hasMore` false); All shows the server's total.
 */
export function candidatePills(
  rows: Pick<Trainee, "cohort_id" | "user_id" | "invitation_pending" | "access_revoked">[],
  cohorts: Pick<Cohort, "id" | "name">[],
  total: number,
  hasMore: boolean,
): CandidatePill[] {
  const withCount = (label: string, n: number) => (hasMore ? label : `${label} ${n}`);
  return [
    { key: "all", label: `All ${total}` },
    ...cohorts.map((c) => ({
      key: { intake: c.id } as CandidatePillKey,
      label: withCount(c.name, rows.filter((r) => r.cohort_id === c.id).length),
    })),
    { key: "invited", label: withCount("Invited, not joined", rows.filter(isInvitedNotJoined).length) },
  ];
}

export function filterByPill<T extends Pick<Trainee, "cohort_id" | "user_id" | "invitation_pending" | "access_revoked">>(rows: T[], key: CandidatePillKey): T[] {
  if (key === "all") return rows;
  if (key === "invited") return rows.filter(isInvitedNotJoined);
  return rows.filter((r) => r.cohort_id === key.intake);
}

export const CANDIDATES_DESC = "The people you are assessing. Group them by intake to schedule them together.";
export const CANDIDATES_SEARCH = "Search by name or email";
export const CANDIDATES_BULK_HINT = "Select candidates to move them to an intake, resend invitations or remove their access.";
export const CANDIDATES_EMPTY = {
  title: "No candidates yet",
  body: "Paste their emails or upload a spreadsheet. They are invited when you schedule an assessment.",
};

const EMAIL = /^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/;

type PastedEmails = { emails: string[]; invalid: string[]; duplicates: string[] };

/** One address per line (commas and semicolons also split). Addresses already on the list or repeated are duplicates. */
export function parsePastedEmails(text: string, existing: string[]): PastedEmails {
  const known = new Set(existing.map((e) => e.trim().toLowerCase()));
  const seen = new Set<string>();
  const out: PastedEmails = { emails: [], invalid: [], duplicates: [] };
  for (const raw of text.split(/[\n,;]+/)) {
    const address = raw.trim();
    if (!address) continue;
    const key = address.toLowerCase();
    if (!EMAIL.test(address)) out.invalid.push(address);
    else if (known.has(key) || seen.has(key)) {
      if (!out.duplicates.some((d) => d.toLowerCase() === key)) out.duplicates.push(address);
    } else {
      seen.add(key);
      out.emails.push(address);
    }
  }
  return out;
}

export function duplicateWarning(duplicates: string[]): string | null {
  if (duplicates.length === 0) return null;
  const [first] = duplicates;
  return duplicates.length === 1
    ? `${first} is already a candidate. We will skip it.`
    : `${duplicates.length} addresses are already candidates. We will skip them.`;
}

export function addCandidatesLabel(count: number): string {
  return count === 0 ? "Add candidates" : `Add ${count} ${count === 1 ? "candidate" : "candidates"}`;
}

/** Why the primary is disabled, said beneath it; null when it is ready. */
export function addCandidatesBlocked(parsed: PastedEmails, busy: boolean): string | null {
  if (busy) return null;
  if (parsed.emails.length > 0) return null;
  if (parsed.invalid.length > 0) return `${parsed.invalid[0]} is not a usable email address.`;
  if (parsed.duplicates.length > 0) return "Every address is already a candidate.";
  return "Enter at least one email address.";
}
