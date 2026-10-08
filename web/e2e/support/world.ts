/**
 * The world global-setup builds once per run: a fresh institution with one
 * account per role, an active SCA programme, and a pool of library stations.
 * Specs read it back with `world()`.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

/** Playwright runs from web/. */
export const WORLD_FILE = join(process.cwd(), "e2e", ".auth", "world.json");

export type Role = "admin" | "supervisor" | "trainee" | "consumer" | "newcomer";

export interface World {
  slug: string;
  orgName: string;
  accounts: Record<Role, { email: string; name: string }>;
  traineeUserId: string;
  programmeId: string;
  stationVersionIds: string[];
}

export function world(): World {
  return JSON.parse(readFileSync(WORLD_FILE, "utf8")) as World;
}
