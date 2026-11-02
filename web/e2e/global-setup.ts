import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { ADMIN, API, assertLocalApi, call, login, PASSWORD, register, stamp, switchWorkspace } from "./support/api";
import { ensureScaPlanOnSale } from "./support/db";
import { stagingWorld } from "./support/staging";
import { WORLD_FILE, type Role, type World } from "./support/world";

function writeWorld(built: World): void {
  mkdirSync(dirname(WORLD_FILE), { recursive: true });
  writeFileSync(WORLD_FILE, JSON.stringify(built, null, 2));
}

/**
 * A brief the trainee can read: the SCA template's required patient blocks, and the candidate's biodata.
 * The history is as long as a real station's, so a phone has to scroll to the end of it (TRAIN-8).
 */
const LIBRARY_CONTENT = {
  patient_biodata: "Sam Reid, 54",
  gender: "male",
  opening_sentence: "I've had this cough for three weeks.",
  expanded_history: [
    "Dry cough for three weeks, worse at night and when lying flat; it wakes you two or three times a night.",
    "No phlegm, no blood, no weight loss, no night sweats. Mildly short of breath walking up the hill to the shops.",
    "You had a cold beforehand that settled. You stopped smoking ten years ago after twenty years of ten a day.",
    "You take ramipril 5 mg for blood pressure, started about two months ago. No allergies. You live with your wife.",
    "You are worried because your brother was diagnosed with lung cancer last year, and you want a chest X-ray today.",
    "If asked, the cough began a week or two after the ramipril, and you have not mentioned it to anyone yet.",
  ].join(" "),
  doctor_patient_biodata: "Sam Reid, 54, retired teacher",
};

/**
 * A fresh database has no station library (seed_platform.py imports none), so a run on one
 * authors three minimal SCA stations as the platform admin, on the SCA platform template
 * (scripts/seed_station_templates.py) so the brief has sections. Skipped when the library has them.
 */
async function ensureLibrary(platform: string): Promise<string[]> {
  const ids = async () => ((await call(platform, "/api/v1/stations?exam_code=sca&limit=3")).items as { version_id: string }[]).map((item) => item.version_id);
  let have = await ids();
  if (have.length < 3) {
    const templates = (await call(platform, "/api/v1/platform/station-templates?exam_code=sca&published_only=true")).items as {
      exam_code: string | null;
      versions: { id: string; status: string }[];
    }[];
    // The filter also answers templates for any exam (the ASPiH one), which have no SCA blocks.
    const templateVersionId = templates
      .filter((t) => t.exam_code === "sca")
      .flatMap((t) => t.versions).find((v) => v.status === "published")?.id;
    if (!templateVersionId) throw new Error("no published SCA station template: run scripts/seed_station_templates.py --apply");
    for (let n = have.length; n < 3; n += 1) {
      const title = `E2E library station ${n + 1}`;
      const created = await call(platform, "/api/v1/platform/stations", {
        method: "POST",
        body: { title, exam_code: "sca", template_version_id: templateVersionId, content: { title, ...LIBRARY_CONTENT } },
      });
      await call(platform, `/api/v1/platform/stations/${created.id}/versions/1/publish`, { method: "POST" });
      // The library shows approved stations only, so an editor's sign-off follows the publish.
      await call(platform, `/api/v1/platform/stations/${created.id}/approve`, { method: "POST" });
    }
    have = await ids();
  }
  return have;
}

export default async function globalSetup(): Promise<void> {
  if (process.env.E2E_TARGET === "staging") {
    // Staging is read-only here: the accounts exist already and the specs create nothing.
    writeWorld(stagingWorld());
    console.log("e2e world: staging accounts from STAGING_E2E_* secrets");
    return;
  }
  // Before anything writes: the specs create organisations and accounts.
  assertLocalApi();
  const health = await fetch(`${API}/health`).catch(() => null);
  if (!health?.ok) throw new Error(`platform-api is not answering at ${API}. Start it first (docs/CORE-JOURNEYS.md).`);

  const id = stamp();
  const slug = `e2e-${id}`;
  const orgName = `E2E Institute ${id}`;
  const hireSlug = `e2e-hire-${id}`;
  const partnerSlug = `e2e-partner-${id}`;
  const person = (key: string, name: string) => ({ email: `e2e-${key}-${id}@example.com`, name, password: PASSWORD });
  const accounts: World["accounts"] = {
    admin: person("admin", "Ada Admin"),
    supervisor: person("sup", "Sam Supervisor"),
    trainee: person("trainee", "Tess Trainee"),
    consumer: person("learner", "Lena Learner"),
    newcomer: person("newcomer", "Nia Newcomer"),
    runner: person("runner", "Remi Runner"),
    hireAdmin: person("hire-admin", "Hugo Hirer"),
    hireCandidate: person("hire-candidate", "Cass Candidate"),
    partnerAdmin: person("partner-admin", "Pia Partner"),
    // The seeded platform admin: already exists, so it is not registered below.
    platform: { email: ADMIN.email, name: "Platform admin", password: ADMIN.password },
  };
  /** Which organisation and role each account joins; the rest are plain accounts. */
  const memberships: Partial<Record<Role, { slug: string; role: string }>> = {
    admin: { slug, role: "institution_admin" },
    supervisor: { slug, role: "supervisor" },
    trainee: { slug, role: "trainee" },
    hireAdmin: { slug: hireSlug, role: "institution_admin" },
    hireCandidate: { slug: hireSlug, role: "trainee" },
    partnerAdmin: { slug: partnerSlug, role: "partner_admin" },
  };

  const platform = await login(ADMIN.email, ADMIN.password);
  await call(platform, "/api/v1/platform/organizations", {
    method: "POST",
    body: { name: orgName, slug, org_type: "institution" },
  });
  for (const [orgSlug, name, orgType] of [
    [hireSlug, `E2E Employer ${id}`, "employer"],
    [partnerSlug, `E2E Partner ${id}`, "partner"],
  ]) {
    await call(platform, "/api/v1/platform/organizations", { method: "POST", body: { name, slug: orgSlug, org_type: orgType } });
  }
  for (const role of Object.keys(accounts) as Role[]) {
    if (role === "platform") continue;
    await register(accounts[role].email, accounts[role].name);
    const member = memberships[role];
    if (!member) continue;
    await call(platform, `/api/v1/platform/organizations/${member.slug}/memberships`, {
      method: "POST",
      body: { email: accounts[role].email, role: member.role },
    });
  }

  // Learners who have picked their exam; the newcomer has not, so sees the exam picker.
  for (const role of ["consumer", "runner"] as const) {
    await call(await login(accounts[role].email, PASSWORD), "/api/v1/me", { method: "PATCH", body: { exam_code: "sca" } });
  }

  // The null-exam journeys (TRAIN-13) break the dashboard and then expect the retry to bring this exam back.
  const learnerDashboard = await call(await login(accounts.consumer.email, PASSWORD), "/api/v1/me/dashboard");
  if (learnerDashboard.current_exam_code !== "sca") {
    throw new Error(
      `the consumer's dashboard names ${String(learnerDashboard.current_exam_code)}, not sca: seed the exams with api/scripts/seed_platform.py`,
    );
  }

  // The admin sets the institution up the way the console would.
  const admin = await switchWorkspace(await login(accounts.admin.email, PASSWORD), slug);
  const programme = await call(admin, `/api/v1/orgs/${slug}/programmes`, { method: "POST", body: { exam_code: "sca" } });
  await call(admin, `/api/v1/orgs/${slug}/programmes/${programme.id}`, { method: "PATCH", body: { status: "active" } });
  // The setup guide counts a template only once the organisation holds its own copy of one.
  const platformTemplates = (await call(platform, "/api/v1/platform/station-templates?exam_code=sca&published_only=true")).items as {
    id: string;
    exam_code: string | null;
  }[];
  const scaTemplate = platformTemplates.find((t) => t.exam_code === "sca");
  if (!scaTemplate) throw new Error("no published SCA station template: run scripts/seed_station_templates.py --apply");
  await call(admin, `/api/v1/orgs/${slug}/station-templates/${scaTemplate.id}/copy`, { method: "POST" });
  const trainee = await call(admin, `/api/v1/orgs/${slug}/trainees`, {
    method: "POST",
    body: { email: accounts.trainee.email, first_name: "Tess", last_name: "Trainee" },
  });
  const stationVersionIds = await ensureLibrary(platform);
  if (stationVersionIds.length === 0) throw new Error("no published SCA stations: run scripts/seed_platform.py");
  ensureScaPlanOnSale();

  writeWorld({
    target: "local",
    slug,
    orgName,
    hireSlug,
    partnerSlug,
    accounts,
    traineeUserId: trainee.user_id as string,
    programmeId: programme.id as string,
    stationVersionIds,
  });
  console.log(`e2e world: org ${slug} on ${API}`);
}
