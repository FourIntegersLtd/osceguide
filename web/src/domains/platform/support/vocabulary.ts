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
  inactive: "Dormant. Members can sign in but cannot open the organisation.",
  suspended: "Paused by us. Members can sign in but cannot open the organisation.",
  churned: "A former customer. Members can sign in but cannot open the organisation.",
};

/**
 * The kinds the backend will provision (`CreateOrganization.org_type`). An employer runs
 * exam-mode sittings and gets the Hire workspace.
 */
export const ORG_TYPES = [
  { value: "institution", label: "Institution" },
  { value: "partner", label: "Partner" },
  { value: "employer", label: "Employer" },
] as const;

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** The backend's `CreateOrganization.slug`: `^[a-zA-Z0-9][a-zA-Z0-9-]*$`, 2 to 100 characters. */
const SLUG_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9-]*$/;

/**
 * Why the API would refuse this slug, or null. Checked before sending, so the
 * person sees which field is wrong instead of "The request was not valid".
 */
export function slugError(slug: string): string | null {
  const value = slug.trim();
  if (!value) return null;
  if (value.length < 2 || value.length > 100) return "A slug is 2 to 100 characters long.";
  if (!SLUG_PATTERN.test(value)) {
    return "Use only letters, numbers and hyphens, starting with a letter or number.";
  }
  return null;
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

export const CONTRACT_DATES_OUT_OF_ORDER = "The end date is before the start date";

/**
 * The message for the End date field when the contract would end before it
 * starts, or null. A blank field stands for the stored date, because saving
 * leaves a blank one alone; ISO day strings compare correctly as text. The
 * API refuses the same pair (`contract_dates_out_of_order`) and stays the authority.
 */
export function contractDatesError(
  startsAt: string,
  endsAt: string,
  stored: { startsAt: string; endsAt: string },
): string | null {
  const start = startsAt.trim() || stored.startsAt;
  const end = endsAt.trim() || stored.endsAt;
  return start && end && start > end ? CONTRACT_DATES_OUT_OF_ORDER : null;
}

export const RENEWAL_IN_PAST = "A renewal must end in the future";

/**
 * Why the API would refuse this renewal date (`contract_end_in_past`), or null. A day is
 * read as its midnight, so today is already past; the API stays the authority.
 */
export function renewalDateError(endsAt: string, today: string): string | null {
  const end = endsAt.trim();
  return end && end <= today ? RENEWAL_IN_PAST : null;
}

/** Today's date in the browser's own time zone, as `YYYY-MM-DD`. */
export function localDay(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export interface SsoFormValues {
  issuer: string;
  enabled: boolean;
  sso_only: boolean;
}

export interface SsoFieldErrors {
  issuer?: string;
  sso_only?: string;
}

/** What the API's `ensure_configurable` would refuse, as messages for the fields at fault. */
export function ssoFieldErrors(form: SsoFormValues): SsoFieldErrors {
  const errors: SsoFieldErrors = {};
  if (form.enabled && !form.issuer.trim()) {
    errors.issuer = "An issuer is required before SSO can be turned on.";
  }
  if (form.sso_only && !form.enabled) {
    errors.sso_only = "Turn on Enabled first: SSO-only sign-in needs SSO switched on.";
  }
  return errors;
}

/**
 * "3 days ago (3 Oct 2026)" — when something last happened, for a fact a
 * support agent compares with "now". `null` means it never has.
 */
export function formatSince(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "Never";
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return iso;
  const minutes = Math.max(0, Math.floor((now.getTime() - at.getTime()) / 60_000));
  const ago = (n: number, unit: string) => `${n} ${unit}${n === 1 ? "" : "s"} ago`;
  const since =
    minutes < 1
      ? "Just now"
      : minutes < 60
        ? ago(minutes, "minute")
        : minutes < 60 * 24
          ? ago(Math.floor(minutes / 60), "hour")
          : // Calendar days, so 3 Oct read on 6 Oct is "3 days ago" whatever the hour.
            ago(Math.max(1, Math.round((startOfDay(now) - startOfDay(at)) / 86_400_000)), "day");
  return `${since} (${formatDay(iso)})`;
}

const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();

/** "3 Sept 2026" — the console's date, for a row rather than a field. */
export function formatDay(iso: string | null | undefined): string {
  if (!iso) return "-";
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
/** A consultation can legitimately run this long; younger than this is treated as live. */
const LIVE_WINDOW_MINUTES = 30;

export function diagnoseAttempt(attempt: {
  status: string;
  transcript_complete: boolean;
  result_policy_versions: string[];
  scoring_job: { status: string } | null;
  chunk_count?: number;
  has_definition?: boolean;
  started_at?: string | null;
  created_at?: string;
}, now: number = Date.now()): { problem: string; action: "salvage" | "rescore" | "fail" | null } | null {
  const status = attempt.status;
  if (status === "evaluated" || status === "failed") return null;
  if (status === "created" || status === "running") {
    const since = Date.parse(attempt.started_at ?? attempt.created_at ?? "");
    const minutes = Math.floor((now - since) / 60_000);
    if (Number.isFinite(since) && minutes < LIVE_WINDOW_MINUTES) {
      return {
        problem: `This consultation began ${minutes < 1 ? "less than a minute" : `${minutes} minute${minutes === 1 ? "" : "s"}`} ago and may still be in progress. Failing or salvaging it now would end it for the person sitting it.`,
        action: null,
      };
    }
  }
  if (status === "created") {
    return { problem: "The room was never joined, so nothing was recorded.", action: "fail" };
  }
  if (status === "running") {
    if (attempt.has_definition === false) {
      return { problem: "The AI patient never loaded this station, so there is nothing to mark.", action: "fail" };
    }
    if ((attempt.chunk_count ?? 1) === 0) {
      return { problem: "The session opened but nothing that was said was recorded.", action: "fail" };
    }
    return {
      problem: "Part of the conversation was recorded, but the full transcript never arrived.",
      action: "salvage",
    };
  }
  // interaction_complete: the transcript is in; the marking is the question.
  if (attempt.result_policy_versions.length > 0) return null;
  const job = attempt.scoring_job;
  if (!job) return { problem: "The transcript arrived but it was never sent for marking.", action: "rescore" };
  if (job.status === "failed" || job.status === "aborted") {
    return { problem: "The marking failed.", action: "rescore" };
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

/** "3 Sept 2026, 14:05" — for a row where the time of day matters. */
export function formatMoment(iso: string | null | undefined): string {
  if (!iso) return "-";
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
