/**
 * The world global-setup builds once per run: a fresh institution with one
 * account per role, an employer and a partner organisation, an active SCA
 * programme, and a pool of library stations. Specs read it back with `world()`.
 *
 * Against staging (E2E_TARGET=staging) nothing is built: the world is read from
 * the STAGING_E2E_* secrets (e2e/support/staging.ts), and a role whose secrets
 * are absent has an empty email, which `needRole` turns into a skip.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "@playwright/test";

/** Playwright runs from web/. */
export const WORLD_FILE = join(process.cwd(), "e2e", ".auth", "world.json");

export const ROLES = [
  "admin",
  "supervisor",
  "trainee",
  "consumer",
  "newcomer",
  "hireAdmin",
  "hireCandidate",
  "partnerAdmin",
  "platform",
] as const;
export type Role = (typeof ROLES)[number];

export interface Account {
  email: string;
  name: string;
  password: string;
}

export interface World {
  /** "local" builds and writes its own data; "staging" only reads what the secrets name. */
  target: "local" | "staging";
  /** The institution (Assess arm). */
  slug: string;
  orgName: string;
  /** The employer organisation (Hire arm). */
  hireSlug: string;
  /** The partner organisation (Partner arm). */
  partnerSlug: string;
  accounts: Record<Role, Account>;
  traineeUserId: string;
  programmeId: string;
  stationVersionIds: string[];
}

export function world(): World {
  return JSON.parse(readFileSync(WORLD_FILE, "utf8")) as World;
}

/** Skip the calling test when this role has no account (staging without its secrets). */
export function needRole(...roles: Role[]): void {
  const w = world();
  const missing = roles.filter((role) => !w.accounts[role].email);
  test.skip(missing.length > 0, `no ${missing.join(", ")} account for this target (set the STAGING_E2E_* secrets)`);
}
