/**
 * The staff console's vocabulary and its pure decisions.
 *
 * Kept out of the components so the directory's filtering, the status
 * vocabulary and the contract-date conversion can be tested without rendering
 * anything — the retiring console had all three inline in a 589-line page.
 */
import type { Organization } from "@/domains/platform/api";

/**
 * The statuses an organisation can be in, and what each one means for signing in.
 *
 * `trial` and `active` permit access; the rest do not. That is the backend's
 * `ACTIVE_ORG_STATUSES`, and it is the reason this list is not just labels: an
 * administrator choosing a status is deciding whether a tenant can work today.
 */
export const ORG_STATUSES = ["trial", "active", "inactive", "suspended", "churned"] as const;

export type OrgStatus = (typeof ORG_STATUSES)[number];

const SIGN_IN_PERMITTED = new Set<string>(["trial", "active"]);

export function permitsSignIn(status: string | null | undefined): boolean {
  return SIGN_IN_PERMITTED.has(String(status ?? "").trim().toLowerCase());
}

export function statusTone(status: string | null | undefined): "success" | "warning" | "neutral" {
  const normalized = String(status ?? "active").trim().toLowerCase();
  if (normalized === "active") return "success";
  if (normalized === "trial") return "warning";
  return "neutral";
}

export const STATUS_HELP: Record<string, string> = {
  trial: "Evaluation. Members can sign in.",
  active: "Normal operation. Members can sign in.",
  inactive: "Dormant. Members cannot sign in.",
  suspended: "Paused by us. Members cannot sign in.",
  churned: "A former customer. Members cannot sign in.",
};

/**
 * The two kinds the backend will provision.
 *
 * An employer is an institution running exam-mode sittings rather than a third
 * kind — `CreateOrganization.org_type` admits `institution` and `partner`, and
 * offering a third here would be a 422 an administrator could not explain.
 */
export const ORG_TYPES = [
  { value: "institution", label: "Institution" },
  { value: "partner", label: "Partner" },
] as const;

/** The roles worth seating a first member as. An org admin adds everyone else. */
export const SEAT_ROLES = [
  { value: "owner", label: "Owner" },
  { value: "admin", label: "Administrator" },
  { value: "institution_admin", label: "Institution administrator" },
  { value: "partner_admin", label: "Partner administrator" },
] as const;

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** Name or slug, case-insensitively. An empty term matches everything. */
export function matchesSearch(organization: Organization, term: string): boolean {
  const needle = term.trim().toLowerCase();
  if (!needle) return true;
  return (
    organization.name.toLowerCase().includes(needle) ||
    organization.slug.toLowerCase().includes(needle)
  );
}

/**
 * A `<input type="date">` value as the backend's `date-time`.
 *
 * Midnight UTC, because a contract that ends on the 19th has ended at the
 * start of the 19th — the sweep that suspends a lapsed tenant compares
 * `now >= contract_ends_at`, so any other hour would leave a tenant working
 * into a day it has not paid for.
 *
 * An empty field is `null` — clear this date — rather than `undefined`, which
 * means leave it alone. The two are different intentions and the form has to
 * be able to say both.
 */
export function asContractDate(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? `${trimmed}T00:00:00Z` : null;
}

/** "3 Sept 2026" — the console's date, for a row rather than a field. */
export function formatDay(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}
