/**
 * Seeds an organisation with the sample state of the People and Add people boards
 * (docs/institution-overhaul/boards/People.dc.html), through existing api routes. Two rows of
 * sample state have no route and are set with the one database seam the other specs use
 * (db.ts): a person "who has signed in" (users.last_login_at), and a roster row with no account
 * (trainees.user_id null, which the api no longer creates). Everything the api derives from real
 * exam activity (programme names, stations sat) cannot be made without a marked sitting and is a
 * named exception in board-people.spec.ts.
 */
import { call, createOrg, orgPath, type SeededOrg } from "./api";
import { psql, q } from "./db";

export type PeopleOrg = SeededOrg;

/**
 * The board writes its people at stmarys.ac.uk. Seeding queues a real invitation email per address
 * (roster/service.py seat_or_invite), so every seeded address uses the reserved example.com domain (a .test address is refused by the api's email validator) instead.
 * Named exception: the board's text is six characters longer ("stmarys.ac.uk" against "stmarys.example.com");
 * the narrow email column is compared with the address text masked in board-people.spec.ts.
 */
export const DOMAIN = "stmarys.example.com";
export const addr = (name: string) => `${name}@${DOMAIN}`;

/** The signed-in owner, okafor, of a fresh organisation named "St Mary's" (an address unique to this run). */
export async function seedPeopleOrg(): Promise<PeopleOrg> {
  return createOrg({ prefix: "people", role: "owner", adminName: "Okafor" });
}

/**
 * Whether these addresses have signed in is stored on the user, and the board's addresses are the same in every run
 * and spec (addr()), so state a previous run left would show here. Seeding sets it explicitly: never signed in
 * (the default for anyone this org adds) or, with `haveSignedIn`, signed in.
 */
function setLastLogin(emails: string[], value: "now()" | "NULL"): void {
  if (emails.length === 0) return;
  psql(`UPDATE users SET last_login_at = ${value} WHERE email IN (${emails.map(q).join(",")});`);
}

/** Mark these addresses as people who have signed in (no "invited, not accepted"). */
export const haveSignedIn = (emails: string[]) => setLastLogin(emails, "now()");

export async function addCohorts(org: PeopleOrg, cohorts: { name: string; year: string | null }[]): Promise<Record<string, string>> {
  const ids: Record<string, string> = {};
  for (const c of cohorts) {
    const made = await call<{ id: string }>(org.token, orgPath(org.slug, `/cohorts`), { method: "POST", body: { name: c.name, academic_year: c.year } });
    ids[c.name] = made.id;
  }
  return ids;
}

export interface Person {
  first: string;
  last: string;
  email: string;
  cohort?: string | null;
}

/** The api's MAX_BULK_TRAINEES (api/app/features/roster/schemas.py). */
const BULK_LIMIT = 100;

export async function addTrainees(org: PeopleOrg, people: Person[]): Promise<Record<string, string>> {
  const ids: Record<string, string> = {};
  for (let at = 0; at < people.length; at += BULK_LIMIT) {
    const batch = people.slice(at, at + BULK_LIMIT);
    const made = await call<{ created: { id: string; email: string }[]; skipped?: unknown[] }>(org.token, orgPath(org.slug, `/trainees/bulk`), {
      method: "POST",
      body: { trainees: batch.map((p) => ({ email: p.email, first_name: p.first, last_name: p.last, cohort_id: p.cohort ?? null })) },
    });
    if ((made.skipped?.length ?? 0) > 0 || made.created.length !== batch.length) throw new Error(`bulk add kept ${made.created.length} of ${batch.length}: ${JSON.stringify(made.skipped)}`);
    for (const row of made.created) ids[row.email] = row.id;
    setLastLogin(batch.map((p) => p.email), "NULL");
  }
  return ids;
}

export async function addStaff(org: PeopleOrg, staff: { email: string; role: "supervisor" | "admin" }[]): Promise<Record<string, string>> {
  const ids: Record<string, string> = {};
  for (const s of staff) {
    const made = await call<{ id: string }>(org.token, orgPath(org.slug, `/memberships`), { method: "POST", body: { email: s.email, role: s.role } });
    ids[s.email] = made.id;
  }
  setLastLogin(staff.map((s) => s.email), "NULL");
  return ids;
}

export async function addGroup(org: PeopleOrg, label: string, traineeIds: string[]): Promise<string> {
  const made = await call<{ id: string }>(org.token, orgPath(org.slug, `/trainee-groups`), { method: "POST", body: { label } });
  if (traineeIds.length > 0) {
    await call(org.token, orgPath(org.slug, `/trainee-groups/${made.id}/members`), { method: "PUT", body: { trainee_ids: traineeIds } });
  }
  return made.id;
}

/** A roster row with no account at all, "Added, no account yet" (the api now always links one). */
export function unlinkAccount(orgSlug: string, email: string): void {
  psql(`UPDATE trainees SET user_id = NULL WHERE email = ${q(email)} AND org_id = (SELECT id FROM organizations WHERE slug = ${q(orgSlug)});`);
}

/** The board's trainees page: 48 people, the first five named, the other 43 signed in so they are not "not joined". */
export const BOARD_FIVE: Person[] = [
  { first: "Amara", last: "Okoye", email: addr("amara") },
  { first: "Ben", last: "Hart", email: addr("ben") },
  { first: "Chloe", last: "Imran", email: addr("chloe") },
  { first: "Dev", last: "Shah", email: addr("dev") },
  { first: "Esme", last: "Lowe", email: addr("esme") },
];

export function fillers(count: number): Person[] {
  return Array.from({ length: count }, (_, n) => ({
    first: `Filler${String(n + 1).padStart(2, "0")}`,
    last: "Person",
    email: addr(`filler${String(n + 1).padStart(2, "0")}`),
  }));
}
