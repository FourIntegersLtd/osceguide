/**
 * Seeds an organisation with the sample state of the Exams, New exam and New station boards
 * (docs/institution-overhaul/boards/Exams.dc.html): three exams, three marking schemes, four station
 * templates, three programmes and three stations, through existing api routes only.
 * What the api cannot be made to show is a named exception in the spec, not a mask.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { ADMIN, call, createOrg, login, orgPath, register, switchWorkspace, type SeededOrg } from "./api";
import { userIdByEmail } from "./db";
import { ensureStations, seedSitting, type SittingsOrg } from "./seed-sittings";

export type ExamsOrg = SeededOrg;

const PACING = { total_seconds: 720, history_seconds: 360, introduction_seconds: 30, safety_net_seconds: 120 };
const PROMPT = "You are marking a consultation. Fill every field of the schema.";

/** The smallest publishable rubric (api/app/features/rubrics/authoring.py blank_structure). */
function structure(domains?: string[]): Record<string, unknown> {
  const section = (id: string, title: string, competencies: unknown[]) => ({
    id,
    title,
    kind: "domain",
    instructions: "",
    competencies,
    competencyFields: [
      { id: "score", type: "rating", role: "rating", label: "Rating" },
      { id: "evidence", type: "longText", role: "evidence", label: "Evidence" },
      { id: "explanation", type: "longText", role: "explanation", label: "Explanation" },
    ],
  });
  return {
    schemaVersion: 2,
    rating: { kind: "rag", field: "score" },
    // Named domains (the Slot review board's three areas), each with the one competency a domain needs to publish.
    sections: domains
      ? domains.map((title, n) => section(`domain_${n + 1}`, title, [{ id: "competency_1", label: "Approach", instructions: "" }]))
      : [section("domain_1", "Domain 1", [{ id: "competency_1", label: "Competency 1", instructions: "" }])],
  };
}

/** The body of a rubric create or add-version call: {structure, system_prompt, pacing}. */
export function blankRubricBody(domains?: string[]): { structure: Record<string, unknown>; system_prompt: string; pacing: typeof PACING } {
  return { structure: structure(domains), system_prompt: PROMPT, pacing: PACING };
}

export interface Rubric { id: string; versions: { id: string; version: number }[] }

export async function rubric(token: string, slug: string, title: string, published: number, drafts: number, domains?: string[]): Promise<Rubric> {
  const base = orgPath(slug, `/rubrics`);
  const body = blankRubricBody(domains);
  const made = await call<Rubric>(token, base, { method: "POST", body: { title, ...body } });
  const addVersion = () => call(token, `${base}/${made.id}/versions`, { method: "POST", body });
  // The first version exists; each later one is added, and the first `published` of them go live.
  for (let n = 1; n < published + drafts; n += 1) await addVersion();
  if (published + drafts === 0) return made;
  for (let n = 1; n <= published; n += 1) await call(token, `${base}/${made.id}/versions/${n}/publish`, { method: "POST" });
  const list = await call<{ items: Rubric[] }>(token, base);
  return list.items.find((r) => r.id === made.id) ?? made;
}

/** Create the exam `code` on `rubric_version_id`, publish it and open an active programme for it. */
export async function publishedExam(
  token: string,
  slug: string,
  options: { code: string; name: string; versionId: string | undefined; reading?: number; simulation?: number },
): Promise<{ examId: string; programmeId: string }> {
  const exam = await call<{ id: string }>(token, orgPath(slug, "/exams"), {
    method: "POST",
    body: {
      code: options.code,
      name: options.name,
      default_reading_seconds: options.reading ?? 180,
      default_simulation_seconds: options.simulation ?? 600,
      rubric_version_id: options.versionId,
    },
  });
  await call(token, orgPath(slug, `/exams/${exam.id}/publish`), { method: "POST" });
  const programme = await call<{ id: string }>(token, orgPath(slug, "/programmes"), { method: "POST", body: { exam_code: options.code } });
  await call(token, orgPath(slug, `/programmes/${programme.id}`), { method: "PATCH", body: { status: "active" } });
  return { examId: exam.id, programmeId: programme.id };
}

/** The board's tab 1, 3 and 5 data. */
export async function seedCatalogue(org: ExamsOrg): Promise<void> {
  const { slug, token } = org;
  const scheme = await rubric(token, slug, "Consultation skills", 2, 1);
  await rubric(token, slug, "Final MB global rating", 0, 1);
  const live = scheme.versions.find((v) => v.version === 2);
  // The board's "Final MB OSCE" exam, Live, with its active programme.
  await publishedExam(token, slug, { code: "finals", name: "Final MB OSCE", versionId: live?.id, reading: 120, simulation: 600 });
  await call(token, orgPath(slug, `/exams`), {
    method: "POST",
    body: { code: "y4-mock", name: "Year 4 mock", default_reading_seconds: 120, default_simulation_seconds: 480 },
  });
}

/** The board's "Communication station (v2)": four numbered text areas (CreateStation.dc.html), one long-text block each. */
export function communicationStructure(): Record<string, unknown> {
  const area = (id: string, title: string, description: string) => ({
    id,
    title,
    description,
    audience: "all",
    blocks: [{ id: `${id}_text`, type: "longText", label: title, role: id }],
  });
  return {
    sections: [
      area("candidate_brief", "Candidate brief", "Notes the candidate reads before starting the station."),
      area("patient_script", "Patient script", "The script the simulated patient follows."),
      area("examiner_notes", "Examiner notes", "Model answers and marking notes."),
      area("faculty_notes", "Faculty notes", "Setup, debrief and teaching notes."),
    ],
  };
}

export const STATION_CONTENT = {
  patient_biodata: "Sam Reid, 54",
  gender: "male",
  opening_sentence: "I've had this cough for three weeks.",
  expanded_history: "Dry cough for three weeks, worse at night.",
  doctor_patient_biodata: "Sam Reid, 54, retired teacher",
};

/** The board's tab 2, 4 and 5 data: stations, station templates and programmes. */
export async function seedAuthoring(org: ExamsOrg): Promise<string[]> {
  const { slug, token } = org;
  const notes: string[] = [];
  const attempt = async (what: string, run: () => Promise<unknown>) => {
    try {
      await run();
    } catch (error) {
      notes.push(`${what}: ${(error as Error).message}`);
    }
  };
  const programmes = orgPath(slug, "/programmes");
  // The board's "Year 4 mock, Draft" programme cannot exist: the api refuses a programme on a draft exam.
  // SCA: adopted from the platform, with its programme retired.
  await attempt("adopt sca", async () => {
    const catalogue = (await call<{ items: { exam_id: string; code: string }[] }>(token, orgPath(slug, `/exams/catalog`))).items;
    const sca = catalogue.find((e) => e.code === "sca");
    if (!sca) throw new Error("no platform sca exam");
    await call(token, orgPath(slug, `/exams/import`), { method: "POST", body: { platform_exam_id: sca.exam_id } });
    const programme = await call<{ id: string }>(token, programmes, { method: "POST", body: { exam_code: "sca" } });
    await call(token, `${programmes}/${programme.id}`, { method: "PATCH", body: { status: "active" } });
    await call(token, `${programmes}/${programme.id}`, { method: "PATCH", body: { status: "retired" } });
  });
  // The list is newest first, so create in the reverse of the board's order.
  for (const title of ["Abdominal examination", "Chest pain history", "Breaking bad news"]) {
    await attempt(`station ${title}`, async () => {
      const made = await call<{ id: string }>(token, orgPath(slug, `/stations`), {
        method: "POST",
        body: { title, exam_code: "finals", content: { title, ...STATION_CONTENT } },
      });
      if (title !== "Abdominal examination") await call(token, orgPath(slug, `/stations/${made.id}/versions/1/publish`), { method: "POST" });
    });
  }
  const templates = orgPath(slug, `/station-templates`);
  // A real station layout: the platform's SCA one.
  const platform = await login(ADMIN.email, ADMIN.password);
  const sca = (await call<{ items: { exam_code: string | null; versions: { structure: Record<string, unknown> }[] }[] }>(platform, "/api/v1/platform/station-templates?exam_code=sca&published_only=true")).items.find((t) => t.exam_code === "sca");
  const blocks = sca?.versions[0]?.structure ?? {};
  // Newest first: create in the reverse of the board's order. Communication station is Live v2 with Draft v3.
  await attempt("template Untitled", () => call(token, templates, { method: "POST", body: { title: "Untitled template", exam_code: "finals", structure: blocks } }));
  await attempt("template History and examination", async () => {
    const t = await call<{ id: string }>(token, templates, { method: "POST", body: { title: "History and examination", exam_code: "finals", structure: blocks } });
    await call(token, `${templates}/${t.id}/publish`, { method: "POST" });
  });
  await attempt("template Communication station", async () => {
    const t = await call<{ id: string }>(token, templates, { method: "POST", body: { title: "Communication station", exam_code: "finals", structure: communicationStructure() } });
    await call(token, `${templates}/${t.id}/publish`, { method: "POST" });
    await call(token, `${templates}/${t.id}/versions`, { method: "POST", body: { structure: communicationStructure() } });
    await call(token, `${templates}/${t.id}/publish`, { method: "POST" });
    await call(token, `${templates}/${t.id}/versions`, { method: "POST", body: { structure: communicationStructure() } });
  });
  return notes;
}

const ORG_FILE = join(process.cwd(), "e2e", ".auth", "exams-org.json");

/**
 * The seeded organisation, made once and reused between runs (a run on a fresh one takes a minute):
 * delete e2e/.auth/exams-org.json to start again.
 */
export async function examsOrg(): Promise<ExamsOrg> {
  let account: ExamsOrg["account"] | undefined;
  if (existsSync(ORG_FILE)) {
    const saved = JSON.parse(readFileSync(ORG_FILE, "utf8")) as ExamsOrg;
    account = saved.account;
    try {
      if (process.env.RESEED) throw new Error("reseed");
      return { ...saved, token: await switchWorkspace(await login(saved.account.email, saved.account.password), saved.slug) };
    } catch {
      // The database was reset: seed again.
    }
  }
  const org = await createOrg({ prefix: "exams", role: "institution_admin", adminName: "Board Admin", email: account?.email });
  await seedCatalogue(org);
  const notes = await seedAuthoring(org);
  if (notes.length) console.log(`seed notes:\n${notes.join("\n")}`);
  mkdirSync(dirname(ORG_FILE), { recursive: true });
  writeFileSync(ORG_FILE, JSON.stringify(org));
  return org;
}


/** A published station template of `exam`, returning its published version id. */
async function publishedTemplate(token: string, slug: string, title: string, exam: string, structure: Record<string, unknown>): Promise<string> {
  const base = orgPath(slug, "/station-templates");
  const made = await call<{ id: string }>(token, base, { method: "POST", body: { title, exam_code: exam, structure } });
  await call(token, `${base}/${made.id}/publish`, { method: "POST" });
  const list = await call<{ items: { id: string; versions: { id: string; status: string }[] }[] }>(token, base);
  const version = list.items.find((t) => t.id === made.id)?.versions.find((v) => v.status === "published");
  if (!version) throw new Error(`template ${title} has no published version`);
  return version.id;
}

/**
 * The ExamDetail board's sample (ExamDetail.dc.html): "Final-year OSCE" (FY-OSCE) on St Mary's global rating v3, 17 stations
 * (16 published, Chest pain at v2, Breaking bad news a draft), two layouts, and four sittings of which the first two list:
 * Summer finals on 26 Nov (Scheduled) and March mock today (Running). Only the date a scheme was published cannot match
 * (the api stamps it now) and its words "domains, Green, Amber or Red" are the app's own.
 */
export async function seedExamDetail(): Promise<{ org: SeededOrg; examId: string }> {
  const org = await createOrg({ prefix: "detail", role: "institution_admin", adminName: "Board Admin" });
  const { token, slug } = org;
  const scheme = await rubric(token, slug, "St Mary's global rating", 3, 0, ["Area 1", "Area 2", "Area 3", "Area 4", "Area 5", "Area 6"]);
  const made = await publishedExam(token, slug, { code: "fy-osce", name: "Final-year OSCE", versionId: scheme.versions.find((v) => v.version === 3)?.id, reading: 180, simulation: 600 });
  const history = await publishedTemplate(token, slug, "History and examination", "fy-osce", communicationStructure());
  const communication = await publishedTemplate(token, slug, "Communication skills", "fy-osce", communicationStructure());
  const stations = orgPath(slug, "/stations");
  const station = async (title: string, template: string, publish: boolean): Promise<string> => {
    const row = await call<{ id: string }>(token, stations, { method: "POST", body: { title, exam_code: "fy-osce", template_version_id: template, content: { title, ...STATION_CONTENT } } });
    if (publish) await call(token, `${stations}/${row.id}/versions/1/publish`, { method: "POST" });
    return row.id;
  };
  // The list is newest first: fourteen fillers, then the board's three in reverse.
  for (let n = 1; n <= 14; n += 1) await station(`Filler station ${n}`, history, true);
  await station("Diabetic foot review", history, true);
  await station("Breaking bad news", communication, false);
  const chest = await station("Chest pain in a 54-year-old", history, true);
  await call(token, `${stations}/${chest}/versions`, { method: "POST" });
  await call(token, `${stations}/${chest}/versions/2/publish`, { method: "POST" });

  const email = `detail-candidate-${slug.slice("detail-".length)}@example.com`;
  await register(email, "Board Candidate");
  const trainee = await call<{ id: string; user_id: string | null }>(token, orgPath(slug, "/trainees"), { method: "POST", body: { email, first_name: "Board", last_name: "Candidate" } });
  if (!trainee.user_id) throw new Error("trainee has no linked user");
  const sittingsOrg: SittingsOrg = {
    slug,
    token,
    account: org.account,
    exams: { finals: { examId: made.examId, programmeId: made.programmeId, versionId: "" }, year3: { examId: "", programmeId: "", versionId: "" }, year4: { examId: "", programmeId: "", versionId: "" } },
    stationVersionIds: await ensureStations(1),
    people: [{ name: "Board Candidate", email, userId: userIdByEmail(email), traineeId: trainee.id }],
    staff: {},
    staffAccounts: {},
    cohorts: {},
  };
  const at = (days: number) => { const d = new Date(); d.setUTCDate(d.getUTCDate() + days); d.setUTCHours(9, 0, 0, 0); return d; };
  const nov26 = new Date(Date.UTC(new Date().getUTCFullYear(), 10, 26, 9, 0, 0));
  // Newest first: the two that do not list are created first.
  await seedSitting(sittingsOrg, { name: "Autumn resit", mode: "exam", exam: "finals", scheduledFor: at(60), circuits: [] });
  await seedSitting(sittingsOrg, { name: "Winter mock", mode: "exam", exam: "finals", scheduledFor: at(40), circuits: [] });
  await seedSitting(sittingsOrg, { name: "Summer finals", mode: "exam", exam: "finals", scheduledFor: nov26, circuits: [] });
  await seedSitting(sittingsOrg, { name: "March mock", mode: "exam", exam: "finals", scheduledFor: new Date(), circuits: [{ name: "Circuit 1", people: [0], supervisor: null, stations: 1 }], start: true });
  return { org, examId: made.examId };
}
