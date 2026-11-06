/**
 * Seeds an organisation with the sample state of the Sittings, Sitting and Schedule a sitting boards
 * (docs/institution-overhaul/boards/{Sittings,Sitting,ScheduleSitting}.dc.html) through existing api
 * routes only: three exams,
 * eight library stations, staff, trainees with accounts, sittings with circuits, and the March mock
 * running. What the api cannot be made to show is a named exception in the spec, not a mask.
 */
import { publishedExam, rubric } from "./seed-exams";
import { ADMIN, assertLocalApi, call, createOrg, login, orgPath, PASSWORD, register } from "./api";
import { userIdByEmail } from "./db";

export interface SittingsOrg {
  slug: string;
  token: string;
  account: { email: string; password: string };
  exams: Record<"finals" | "year3" | "year4", { examId: string; programmeId: string; versionId: string }>;
  stationVersionIds: string[];
  people: { name: string; email: string; userId: string; traineeId: string }[];
  staff: Record<string, string>;
  /** Sign-in of each supervisor, by name. */
  staffAccounts: Record<string, { email: string; password: string }>;
  cohorts: Record<string, string>;
}

const LIBRARY_CONTENT = {
  patient_biodata: "Sam Reid, 54",
  gender: "male",
  opening_sentence: "I've had this cough for three weeks.",
  expanded_history: "Dry cough for three weeks, worse at night. No phlegm, no blood, no weight loss.",
  doctor_patient_biodata: "Sam Reid, 54, retired teacher",
};

/**
 * Tops the SCA platform library up to `count` approved stations (as global-setup does for three).
 * This writes "E2E library station N" rows into the platform-wide library, not into the org: it is only
 * ever run against a local api (assertLocalApi). Org-owned stations are not used because the circuit
 * builder offers library stations and the board's "Add from this exam" is a separate path (named exception).
 */
export async function ensureStations(count: number): Promise<string[]> {
  assertLocalApi();
  const platform = await login(ADMIN.email, ADMIN.password);
  const list = async () =>
    ((await call(platform, "/api/v1/stations?exam_code=sca&limit=50")).items as { version_id: string }[]).map((item) => item.version_id);
  let have = await list();
  if (have.length < count) {
    const templates = (await call(platform, "/api/v1/platform/station-templates?exam_code=sca&published_only=true")).items as {
      exam_code: string | null;
      versions: { id: string; status: string }[];
    }[];
    const templateVersionId = templates.filter((t) => t.exam_code === "sca").flatMap((t) => t.versions).find((v) => v.status === "published")?.id;
    if (!templateVersionId) throw new Error("no published SCA station template: run scripts/seed_station_templates.py --apply");
    for (let n = have.length; n < count; n += 1) {
      const title = `E2E library station ${n + 1}`;
      const made = await call(platform, "/api/v1/platform/stations", {
        method: "POST",
        body: { title, exam_code: "sca", template_version_id: templateVersionId, content: { title, ...LIBRARY_CONTENT } },
      });
      await call(platform, `/api/v1/platform/stations/${made.id}/versions/1/publish`, { method: "POST" });
      await call(platform, `/api/v1/platform/stations/${made.id}/approve`, { method: "POST" });
    }
    have = await list();
  }
  return have.slice(0, count);
}

/**
 * Board-like station titles for a spec whose rows wrap with the seed's longer "E2E library station N": finds each title in
 * the library (by exact title) or creates it, and returns their version ids in order. Local api only.
 */
export async function ensureTitledStations(titles: string[]): Promise<string[]> {
  assertLocalApi();
  const platform = await login(ADMIN.email, ADMIN.password);
  const find = async (title: string) =>
    ((await call(platform, `/api/v1/stations?exam_code=sca&limit=50&search=${encodeURIComponent(title)}`)).items as { title: string; version_id: string }[]).find((item) => item.title === title);
  const templates = (await call(platform, "/api/v1/platform/station-templates?exam_code=sca&published_only=true")).items as {
    exam_code: string | null;
    versions: { id: string; status: string }[];
  }[];
  const templateVersionId = templates.filter((t) => t.exam_code === "sca").flatMap((t) => t.versions).find((v) => v.status === "published")?.id;
  if (!templateVersionId) throw new Error("no published sca station template: a station made without one has no brief");
  const ids: string[] = [];
  for (const title of titles) {
    const found = await find(title);
    if (found) {
      ids.push(found.version_id);
      continue;
    }
    const made = await call(platform, "/api/v1/platform/stations", {
      method: "POST",
      body: { title, exam_code: "sca", template_version_id: templateVersionId, content: { title, ...LIBRARY_CONTENT } },
    });
    await call(platform, `/api/v1/platform/stations/${made.id}/versions/1/publish`, { method: "POST" });
    await call(platform, `/api/v1/platform/stations/${made.id}/approve`, { method: "POST" });
    const created = await find(title);
    if (!created) throw new Error(`station "${title}" was not listed after approval`);
    ids.push(created.version_id);
  }
  return ids;
}

const FIRST = ["Amara", "Ben", "Chloe", "Dev", "Esme", "Femi", "Grace", "Hugo", "Isla", "Jonas", "Kira", "Leo", "Maya", "Noor", "Owen", "Pria", "Quinn", "Rosa", "Sami", "Tara", "Umar", "Vera", "Will", "Yara"];
const LAST = ["Okoye", "Hart", "Imran", "Shah", "Walker", "Adeyemi", "Fox", "Lind", "Rao", "Bell", "Stone", "Moss", "Cole", "Haidar", "Price", "Nair", "Reid", "Silva", "Khan", "Boyd", "Rowe", "Quist", "Dunn", "Zahir"];

export interface SeedOptions {
  /** Name of the signed-in administrator (the Sitting board's "Your circuit" belongs to Ms Clarke). */
  adminName: string;
  /** How many trainees with accounts to put on the roster. */
  trainees: number;
  /**
   * Display names for the first trainees, matched literally to the board (e.g. "aisha.bello"). The board's
   * people carry @stmarys.ac.uk emails; the seed uses example.com only, because invitations queue real emails.
   * That is a named exception in the specs.
   */
  names?: string[];
  /** Staff supervisors besides the administrator. */
  supervisors: string[];
  /** Names of the marking scheme's domains, each rated once (default: one "Domain 1" with a competency). */
  domains?: string[];
  /** The kind and name of the organisation (default: the institution "St Mary's Medical School"). */
  org?: { type: "institution" | "employer"; name: string };
}

export async function seedSittingsOrg(options: SeedOptions): Promise<SittingsOrg> {
  const { slug, token, account } = await createOrg({ prefix: "sittings", role: "institution_admin", adminName: options.adminName, orgType: options.org?.type, orgName: options.org?.name });
  const id = slug.slice("sittings-".length);
  const platform = await login(ADMIN.email, ADMIN.password);

  const staff: Record<string, string> = {};
  const staffAccounts: SittingsOrg["staffAccounts"] = {};
  for (const name of options.supervisors) {
    const email = `sittings-${name.toLowerCase().replace(/[^a-z]/g, "")}-${id}@example.com`;
    await register(email, name);
    await call(platform, `/api/v1/platform/organizations/${slug}/memberships`, { method: "POST", body: { email, role: "supervisor" } });
    staff[name] = userIdByEmail(email);
    staffAccounts[name] = { email, password: PASSWORD };
  }
  staff[options.adminName] = userIdByEmail(account.email);

  const scheme = await rubric(token, slug, "Consultation skills", 1, 0, options.domains);
  const rubricVersionId = scheme.versions[0]?.id;
  if (!rubricVersionId) throw new Error("rubric was created without a version");

  const stationVersionIds = await ensureStations(8);
  const examEntries: [keyof SittingsOrg["exams"], SittingsOrg["exams"][keyof SittingsOrg["exams"]]][] = [];
  for (const [key, code, name] of [
    ["finals", "finals", "Final-year OSCE"],
    ["year3", "year3", "Year 3 practice"],
    ["year4", "year4", "Year 4 mock"],
  ] as const) {
    const { examId, programmeId } = await publishedExam(token, slug, { code, name, versionId: rubricVersionId });
    examEntries.push([key, { examId, programmeId, versionId: rubricVersionId }]);
  }
  const exams = Object.fromEntries(examEntries) as SittingsOrg["exams"];

  const cohorts: Record<string, string> = {};
  for (const name of ["Final year 2026", "Year 4", "Year 5"]) {
    cohorts[name] = (await call<{ id: string }>(token, orgPath(slug, `/cohorts`), { method: "POST", body: { name } })).id;
  }

  const people: SittingsOrg["people"] = [];
  for (let n = 0; n < options.trainees; n += 1) {
    const name = options.names?.[n] ?? `${FIRST[n % FIRST.length]} ${LAST[n % LAST.length]}`;
    const email = `sittings-t${n}-${id}@example.com`;
    await register(email, name);
    const added = await call<{ id: string; user_id: string | null }>(token, orgPath(slug, `/trainees`), {
      method: "POST",
      body: { email, first_name: name.split(" ")[0], last_name: name.split(" ").slice(1).join(" ") || "-", cohort_id: cohorts["Year 5"] },
    });
    if (!added.user_id) throw new Error(`trainee ${email} has no linked user`);
    people.push({ name, email, userId: added.user_id, traineeId: added.id });
  }
  return { slug, token, account, exams, stationVersionIds, people, staff, staffAccounts, cohorts };
}

export interface SittingSpec {
  name: string;
  mode: "exam" | "training";
  exam: keyof SittingsOrg["exams"];
  scheduledFor: Date | null;
  /** One circuit per entry: its trainees' indexes in `people`, its supervisor name, how many stations. */
  circuits: { name: string; people: number[]; supervisor: string | null; stations: number }[];
  cohort?: string;
  /** Start the first circuit, which makes the sitting Running. */
  start?: boolean;
  /** Reading time of every circuit; a long one keeps a started room in reading while a board is scored. Default 3. */
  readingMinutes?: number;
}

export async function seedSitting(org: SittingsOrg, spec: SittingSpec): Promise<string> {
  const { slug, token } = org;
  const sitting = await call<{ id: string }>(token, orgPath(slug, `/sittings`), {
    method: "POST",
    body: {
      name: spec.name,
      mode: spec.mode,
      sitting_type: spec.mode === "exam" ? "mock_exam" : "group_training",
      programme_id: org.exams[spec.exam].programmeId,
      scheduled_for: spec.scheduledFor ? spec.scheduledFor.toISOString() : null,
      cohort_id: spec.cohort ? org.cohorts[spec.cohort] : undefined,
    },
  });
  const made: { id: string }[] = [];
  for (const circuit of spec.circuits) {
    made.push(
      await call<{ id: string }>(token, orgPath(slug, `/sittings/${sitting.id}/circuits`), {
        method: "POST",
        body: {
          name: circuit.name,
          station_version_ids: org.stationVersionIds.slice(0, circuit.stations),
          trainee_ids: circuit.people.map((i) => {
            const person = org.people[i];
            if (!person) throw new Error(`circuit "${circuit.name}": no trainee at index ${i}`);
            return person.userId;
          }),
          supervisor_user_id: circuit.supervisor ? staffId(org, circuit.supervisor) : undefined,
          timing: { reading_minutes: spec.readingMinutes ?? 3, simulation_minutes: 10 },
        },
      }),
    );
  }
  if (spec.start && made[0]) await call(token, orgPath(slug, `/circuits/${made[0].id}/start`), { method: "POST" });
  return sitting.id;
}

function staffId(org: SittingsOrg, name: string): string {
  const id = org.staff[name];
  if (!id) throw new Error(`no staff member named ${name}`);
  return id;
}
