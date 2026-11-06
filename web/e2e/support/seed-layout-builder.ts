import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { call, createOrg, login, orgPath, switchWorkspace } from "./api";
import { seedCatalogue, type ExamsOrg } from "./seed-exams";
import { BOARD_STRUCTURE } from "./seed-station-builder";

/**
 * Test data for the LayoutBuilder board spec, in an organisation of its own (the exams org's layout list is shared with
 * other boards). Two layouts: "Communication station" with v1 and v2 published in turn and a draft v3 (the board's edit tab),
 * and "History and examination" with v2 published (the board's read-only tab). Made once; delete e2e/.auth/layout-builder.json to redo.
 */
export interface LayoutBuilderWorld {
  org: ExamsOrg;
  draftId: string;
  publishedId: string;
}

const FILE = join(process.cwd(), "e2e", ".auth", "layout-builder.json");

export async function layoutBuilderWorld(): Promise<LayoutBuilderWorld> {
  if (existsSync(FILE)) {
    const saved = JSON.parse(readFileSync(FILE, "utf8")) as LayoutBuilderWorld;
    try {
      const token = await switchWorkspace(await login(saved.org.account.email, saved.org.account.password), saved.org.slug);
      await call(token, orgPath(saved.org.slug, "/station-templates"));
      return { ...saved, org: { ...saved.org, token } };
    } catch {
      // The database was reset: seed again.
    }
  }
  const org = await createOrg({ prefix: "layouts", role: "institution_admin", adminName: "Board Admin" });
  await seedCatalogue(org);
  const base = orgPath(org.slug, "/station-templates");
  const layout = async (title: string, publishedVersions: number, draft: boolean): Promise<string> => {
    const made = await call<{ id: string }>(org.token, base, { method: "POST", body: { title, exam_code: "finals", structure: BOARD_STRUCTURE } });
    for (let n = 1; n <= publishedVersions; n += 1) {
      await call(org.token, `${base}/${made.id}/publish`, { method: "POST" });
      if (n < publishedVersions || draft) await call(org.token, `${base}/${made.id}/versions`, { method: "POST", body: { structure: BOARD_STRUCTURE } });
    }
    return made.id;
  };
  const world: LayoutBuilderWorld = { org, draftId: await layout("Communication station", 2, true), publishedId: await layout("History and examination", 2, false) };
  mkdirSync(dirname(FILE), { recursive: true });
  writeFileSync(FILE, JSON.stringify(world));
  return world;
}
