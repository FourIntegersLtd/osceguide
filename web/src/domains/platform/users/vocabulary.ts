import type { DirectoryFilters, DirectorySummary, DirectoryUser } from "@/domains/platform/api";

/**
 * The directory's words, kept out of the components so they can be tested
 * without rendering and so two screens cannot spell "not started" two ways.
 */

/** The old filter modal's three states, in its order. */
export const ACCESS_FILTERS = [
  { value: "paid", label: "Paid" },
  { value: "trial", label: "On trial" },
  { value: "not_started", label: "Not started" },
] as const;

export type AccessFilter = (typeof ACCESS_FILTERS)[number]["value"];

/** `users.status` on the backend: `active` or `deactivated`. */
export const USER_STATUSES = [
  { value: "active", label: "Active" },
  { value: "deactivated", label: "Deactivated" },
] as const;

/**
 * Which of the three access states a row is in, from the two facts that
 * decide it — the same rule the backend's `access` facet applies, so a row
 * always sits in the group its filter would find it in.
 */
export function accessOf(user: Pick<DirectoryUser, "has_paid" | "attempt_count">): AccessFilter {
  if (user.has_paid) return "paid";
  return user.attempt_count > 0 ? "trial" : "not_started";
}

export function accessLabel(access: AccessFilter): string {
  return ACCESS_FILTERS.find((entry) => entry.value === access)?.label ?? access;
}

export function accessTone(access: AccessFilter): "success" | "warning" | "neutral" {
  if (access === "paid") return "success";
  if (access === "trial") return "warning";
  return "neutral";
}

export function userStatusTone(status: string): "success" | "danger" {
  return status === "deactivated" ? "danger" : "success";
}

/**
 * "one_month" → "1 month". The retiring console had a table for three codes
 * and printed the raw code for a fourth; the plans come from the backend
 * now, so this reads the code rather than knowing the list.
 */
export function planLabel(code: string | null | undefined): string {
  if (!code) return "No plan";
  const [count, unit] = code.split("_");
  const number = WORDS[count ?? ""] ?? Number(count);
  if (unit && Number.isFinite(number) && number > 0) {
    return `${number} ${unit}${number === 1 ? "" : "s"}`;
  }
  return code.replace(/_/g, " ");
}

const WORDS: Record<string, number> = {
  one: 1,
  two: 2,
  three: 3,
  four: 4,
  five: 5,
  six: 6,
  seven: 7,
  eight: 8,
  nine: 9,
  ten: 10,
  twelve: 12,
};

/** A group heading: "SCA · 412". The code is uppercased for the eye only. */
export function groupTitle(code: string, name: string | null | undefined, count: number): string {
  const label = name?.trim() || code.toUpperCase();
  return `${label} · ${count}`;
}

/**
 * How many rows match this group's filters, when the summary already knows.
 *
 * The directory list is cursor-paged and does not return `total_count`; the
 * summary counts do, for an exam (or access facet) with no name search,
 * status, or plan filter. When those extra filters are on, the total is
 * unknown until the API grows a count — same as the retiring B2C list's
 * `total_count` field, wired here from `GET /platform/directory/summary`.
 */
export function directoryListingTotal(
  summary: DirectorySummary,
  filters: DirectoryFilters,
): number | undefined {
  if (filters.q?.trim() || filters.status || filters.planCode) return undefined;

  if (filters.unassigned) {
    if (filters.access === "paid") return summary.unassigned_paid;
    if (filters.access === "trial") return summary.unassigned_trial;
    if (filters.access) return undefined;
    return summary.unassigned;
  }

  // The whole directory: the same counts the Paid and On trial tiles show.
  if (!filters.examCode) {
    if (filters.access === "paid") return summary.paid;
    if (filters.access === "trial") return summary.trial;
    return undefined;
  }

  const exam = summary.exams.find((entry) => entry.code === filters.examCode);
  if (!exam) return undefined;

  if (filters.access === "paid") return exam.paid;
  if (filters.access === "trial") return exam.trial;
  if (filters.access === "not_started") return exam.not_started;

  return exam.users;
}
