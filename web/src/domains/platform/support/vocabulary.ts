/**
 * The staff console's vocabulary and its pure decisions.
 *
 * Kept out of the components so the directory's filtering, the status
 * vocabulary and the contract-date conversion can be tested without rendering
 * anything — the retiring console had all three inline in a 589-line page.
 */

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

/* ------------------------------------------------------------ Support view */

/** The backend's `attempts.Status`, in the order an attempt moves through them. */
export const ATTEMPT_STATUSES = [
  "created",
  "running",
  "interaction_complete",
  "evaluated",
  "failed",
] as const;

export const ATTEMPT_STATUS_LABELS: Record<string, string> = {
  created: "Created",
  running: "Running",
  interaction_complete: "Awaiting marking",
  evaluated: "Marked",
  failed: "Failed",
};

export function attemptStatusLabel(status: string): string {
  return ATTEMPT_STATUS_LABELS[status] ?? status.replace(/_/g, " ");
}

export function attemptStatusTone(
  status: string | null | undefined,
): "success" | "warning" | "danger" | "neutral" | "info" {
  switch (String(status ?? "").trim().toLowerCase()) {
    case "evaluated":
      return "success";
    case "interaction_complete":
      return "info";
    case "running":
      return "warning";
    case "failed":
      return "danger";
    default:
      return "neutral";
  }
}

/** procrastinate's own vocabulary, coloured by whether somebody should act. */
export function jobStatusTone(
  status: string | null | undefined,
): "success" | "warning" | "danger" | "neutral" | "info" {
  switch (String(status ?? "").trim().toLowerCase()) {
    case "succeeded":
      return "success";
    case "todo":
      return "info";
    case "doing":
      return "warning";
    case "failed":
    case "aborted":
    case "aborting":
      return "danger";
    default:
      return "neutral";
  }
}

/**
 * Why an attempt has no feedback, from what the support read says.
 *
 * The four causes the backend's support view was built to tell apart, in the
 * words a person answering the ticket needs, with the action that fixes each.
 * `null` means nothing is wrong — the marking is done or on its way.
 */
export function diagnoseAttempt(attempt: {
  status: string;
  transcript_complete: boolean;
  result_policy_versions: string[];
  scoring_job: { status: string } | null;
  chunk_count?: number;
  has_definition?: boolean;
}): { problem: string; action: "salvage" | "rescore" | "fail" | null } | null {
  const status = attempt.status;
  if (status === "evaluated" || status === "failed") return null;
  if (status === "created") {
    return { problem: "The room was never joined, so nothing was recorded.", action: "fail" };
  }
  if (status === "running") {
    if (attempt.has_definition === false) {
      return { problem: "The worker never fetched this attempt; nothing was frozen to mark against.", action: "fail" };
    }
    if ((attempt.chunk_count ?? 1) === 0) {
      return { problem: "The session opened but no turns were received.", action: "fail" };
    }
    return {
      problem: "Turns arrived but the worker never delivered the final transcript.",
      action: "salvage",
    };
  }
  // interaction_complete: the transcript is in; the marking is the question.
  if (attempt.result_policy_versions.length > 0) return null;
  const job = attempt.scoring_job;
  if (!job) return { problem: "The transcript arrived but no marking was ever queued.", action: "rescore" };
  if (job.status === "failed" || job.status === "aborted") {
    return { problem: "The marking job failed.", action: "rescore" };
  }
  return null;
}

export const AT_RISK_LABELS: Record<string, string> = {
  suspended: "Suspended",
  contract_lapsed: "Contract lapsed",
  contract_ending: "Contract ending soon",
};

export function atRiskLabel(reason: string): string {
  return AT_RISK_LABELS[reason] ?? reason.replace(/_/g, " ");
}

/** "£24.99" from pence, in the payment's own currency. */
export function formatMoney(pence: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency: currency.toUpperCase(),
    }).format(pence / 100);
  } catch {
    return `${(pence / 100).toFixed(2)} ${currency.toUpperCase()}`;
  }
}

/** "3 Sept 2026, 14:05" — for a row where the time of day matters. */
export function formatMoment(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
