import { existsSync, readFileSync, rmSync } from "node:fs";
import { orgsFile } from "./support/api";
import { deleteOrgs } from "./support/db";

/** Delete the organisations this run created (recorded by createPlatformOrg), so runs stop piling them up in the local database. */
export default async function globalTeardown(): Promise<void> {
  if (process.env.E2E_TARGET === "staging" || !process.env.E2E_RUN_ID || !existsSync(orgsFile())) return;
  const slugs = [...new Set(readFileSync(orgsFile(), "utf8").split("\n").filter(Boolean))];
  try {
    deleteOrgs(slugs);
    rmSync(orgsFile());
    console.log(`e2e teardown: deleted ${slugs.length} organisations`);
  } catch (error) {
    // The ledger stays on disk (e2e/.auth) so the slugs can be deleted by hand.
    console.warn(`e2e teardown: could not delete ${slugs.length} organisations: ${(error as Error).message}`);
  }
}
