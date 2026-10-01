/**
 * A staff spreadsheet, parsed in the browser.
 *
 * Same division the trainee import uses — the file is read here and the API
 * takes rows — and the same reason: an import is then an ordinary JSON call
 * rather than a multipart upload the server re-parses. The line reader is
 * roster's, already tested against quoted fields and a header with a trailing
 * space, so the two importers cannot drift apart on what a row even is.
 *
 * The columns are the ones the old staff upload's own instructions named —
 * `email` and `role` — so a file written for that screen still imports here.
 * What it also named, `password`, is gone: an address with no account is
 * invited and chooses its own password, so a sheet can no longer carry a
 * credential and an administrator no longer relays one.
 */
import { splitCsvLine } from "@/domains/assess/roster/csv";
import { ASSIGNABLE_ROLES, type AssignableRole } from "@/domains/assess/team/support";

/** The backend's `MAX_BULK_MEMBERSHIPS`. One request cannot invite a hospital. */
export const MAX_TEAM_UPLOAD = 500;

export interface StaffRow {
  email: string;
  role: AssignableRole;
}

export interface StaffCsvParse {
  rows: StaffRow[];
  /** Line numbers (1-based, header included) that carried no usable address. */
  skippedLines: number[];
  /** A line whose role column named something this organisation cannot grant. */
  badRoles: { line: number; value: string }[];
  error: string | null;
}

const EMAIL_KEYS = ["email", "emailaddress", "e-mail"];
const ROLE_KEYS = ["role", "access", "staffrole", "usertype"];

/** Header names are matched case- and punctuation-insensitively, as roster's is. */
function normalise(header: string): string {
  return header.trim().toLowerCase().replace(/[\s_]/g, "");
}

/** Words a sheet may use beyond the role names themselves. */
const ROLE_ALIASES: Record<string, AssignableRole> = {
  administrator: "admin",
  "institution admin": "admin",
};

/**
 * Every word that means a grantable role, derived from the screen's own list.
 *
 * `ASSIGNABLE_ROLES` is what the invite form offers, so spelling the accepted
 * words out from it means a row this client can post is never turned away here
 * for want of a synonym table kept in step by hand.
 */
const ROLE_WORDS: Record<string, AssignableRole> = Object.fromEntries([
  ...ASSIGNABLE_ROLES.map((role) => [role, role] as const),
  ...Object.entries(ROLE_ALIASES),
]);

function roleFrom(value: string): AssignableRole | null {
  return ROLE_WORDS[value.trim().toLowerCase()] ?? null;
}

export function parseStaffCsv(text: string): StaffCsvParse {
  const lines = text
    .split(/\r\n|\r|\n/)
    .map((line) => line.trimEnd())
    .filter((line, index) => index === 0 || line.trim() !== "");

  const header = lines[0] ?? "";
  if (header.trim() === "") {
    return { rows: [], skippedLines: [], badRoles: [], error: "That file is empty." };
  }

  const headers = splitCsvLine(header).map(normalise);
  if (!headers.some((entry) => EMAIL_KEYS.includes(entry))) {
    return {
      rows: [],
      skippedLines: [],
      badRoles: [],
      error: "The first row must name the columns, and one of them must be `email`.",
    };
  }

  const rows: StaffRow[] = [];
  const skippedLines: number[] = [];
  const badRoles: { line: number; value: string }[] = [];

  for (let index = 1; index < lines.length; index += 1) {
    const cells = splitCsvLine(lines[index] ?? "");
    const record: Record<string, string> = {};
    headers.forEach((entry, column) => {
      record[entry] = cells[column] ?? "";
    });

    const address = EMAIL_KEYS.map((key) => record[key] ?? "")
      .find((value) => value.trim() !== "")
      ?.trim();
    if (!address || !address.includes("@")) {
      skippedLines.push(index + 1);
      continue;
    }

    const stated = ROLE_KEYS.map((key) => record[key] ?? "")
      .find((value) => value.trim() !== "")
      ?.trim();
    const role = stated ? roleFrom(stated) : null;
    if (!role) {
      badRoles.push({ line: index + 1, value: stated ?? "" });
      continue;
    }

    rows.push({ email: address.toLowerCase(), role });
  }

  if (rows.length === 0) {
    return {
      rows,
      skippedLines,
      badRoles,
      error: "No row in that file had an address and a role we can grant.",
    };
  }
  if (rows.length > MAX_TEAM_UPLOAD) {
    return {
      rows: [],
      skippedLines,
      badRoles,
      error: `That file has ${rows.length} people. One upload takes ${MAX_TEAM_UPLOAD} at most, so split it into smaller sheets.`,
    };
  }
  return { rows, skippedLines, badRoles, error: null };
}

/** Why the backend skipped a row, in words an administrator can act on. */
export function teamSkipReason(code: string): string {
  switch (code) {
    case "membership_exists":
      return "already on the team with that role";
    case "user_not_found":
      return "no account to invite at that address";
    case "invalid_email":
      return "not a usable email address";
    default:
      return code.replace(/_/g, " ");
  }
}
