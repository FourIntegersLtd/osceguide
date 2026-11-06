import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { call, createOrg, login, orgPath, switchWorkspace } from "./api";
import { seedCatalogue, type ExamsOrg } from "./seed-exams";

/**
 * Test data for the StationBuilder and LayoutBuilder board specs: a four-section station layout (the
 * board's Candidate brief, Patient script, Examiner notes, Faculty notes) and three stations on it, one
 * per state the board draws (draft ready, published, archived), each with a v1 archived, v2 published
 * history. Made once per exams org and reused between runs; delete e2e/.auth/station-builder.json to redo.
 */
export interface StationBuilderWorld {
  org: ExamsOrg;
  templateId: string;
  templateVersionId: string;
  draft: string;
  published: string;
  archived: string;
  /** A published station layout with a draft v3 beside it, for the layout builder's edit and view tabs. */
  layoutId: string;
}

const SECTIONS = [
  ["candidate_brief", "Candidate brief", "Notes the candidate reads before starting the station.", "candidate", "candidate_brief"],
  ["patient_script", "Patient script", "The script the simulated patient follows.", "patient", "persona"],
  ["examiner_notes", "Examiner notes", "Model answers and marking notes.", "examiner", "examiner"],
  ["faculty_notes", "Faculty notes", "Setup, debrief and teaching notes.", "faculty", "faculty"],
] as const;

export const BOARD_STRUCTURE = {
  schemaVersion: 1,
  sections: SECTIONS.map(([id, title, description, audience, role]) => ({
    id,
    title,
    description,
    audience,
    blocks: [{ id: `${id}_text`, type: "longText", label: title, role, required: false }],
  })),
};

/** The stations' layout: the same four sections plus the board's Photos card, a media block the station screen draws under the folds. */
export const STATION_STRUCTURE = {
  ...BOARD_STRUCTURE,
  sections: BOARD_STRUCTURE.sections.map((section) =>
    section.id === "faculty_notes" ? { ...section, blocks: [...section.blocks, { id: "photos", type: "media", label: "Photos", required: false }] } : section,
  ),
};

// The board draws every field empty yet the station written: a title keeps it "written" without filling a field.
const CONTENT = { title: "Breaking bad news" };
const FILE = join(process.cwd(), "e2e", ".auth", "station-builder.json");

export async function stationBuilderWorld(): Promise<StationBuilderWorld> {
  if (existsSync(FILE)) {
    const saved = JSON.parse(readFileSync(FILE, "utf8")) as StationBuilderWorld;
    try {
      const token = await switchWorkspace(await login(saved.org.account.email, saved.org.account.password), saved.org.slug);
      await call(token, orgPath(saved.org.slug, `/stations/${saved.draft}`));
      return { ...saved, org: { ...saved.org, token } };
    } catch {
      // The database was reset: seed again.
    }
  }
  // Its own organisation, so the extra stations and layouts never reach the Exams boards' lists.
  const org = await createOrg({ prefix: "builder", role: "institution_admin", adminName: "Board Admin" });
  await seedCatalogue(org);
  const { slug, token } = org;
  const templates = orgPath(slug, "/station-templates");
  const layout = await call<{ id: string }>(token, templates, { method: "POST", body: { title: "Board communication layout", exam_code: "finals", structure: STATION_STRUCTURE } });
  const published = await call<{ id: string }>(token, `${templates}/${layout.id}/publish`, { method: "POST" });
  const templateVersionId = published.id;
  await call(token, `${templates}/${layout.id}/versions`, { method: "POST", body: { structure: STATION_STRUCTURE } });
  const station = async (history: "draft" | "published" | "archived"): Promise<string> => {
    const made = await call<{ id: string }>(token, orgPath(slug, "/stations"), { method: "POST", body: { title: "Breaking bad news", exam_code: "finals", template_version_id: templateVersionId, content: CONTENT } });
    const version = (n: number) => orgPath(slug, `/stations/${made.id}/versions/${n}`);
    await call(token, `${version(1)}/publish`, { method: "POST" });
    await call(token, `${version(1)}/archive`, { method: "POST" });
    if (history === "draft") return made.id;
    await call(token, orgPath(slug, `/stations/${made.id}/versions`), { method: "POST" });
    await call(token, `${version(2)}/publish`, { method: "POST" });
    if (history === "archived") await call(token, `${version(2)}/archive`, { method: "POST" });
    return made.id;
  };
  const world: StationBuilderWorld = { org, templateId: layout.id, templateVersionId, draft: "", published: "", archived: "", layoutId: layout.id };
  // The draft's own history reads v2 published, v1 archived, v3 draft: publish v2, then add the draft.
  const draft = await station("published");
  await call(token, orgPath(slug, `/stations/${draft}/versions`), { method: "POST" });
  world.draft = draft;
  world.published = await station("published");
  world.archived = await station("archived");
  mkdirSync(dirname(FILE), { recursive: true });
  writeFileSync(FILE, JSON.stringify(world));
  return world;
}
