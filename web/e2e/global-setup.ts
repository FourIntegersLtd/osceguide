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

/** A brief the trainee can read: the SCA template's required patient blocks, and the candidate's biodata. */
const LIBRARY_CONTENT = {
  patient_biodata: "Sam Reid, 54",
  gender: "male",
  opening_sentence: "I've had this cough for three weeks.",
  expanded_history: "Dry cough, worse at night, no weight loss.",
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

  // A learner who has picked their exam; the newcomer has not, so sees the exam picker.
  const learner = await login(accounts.consumer.email, PASSWORD);
  await call(learner, "/api/v1/me", { method: "PATCH", body: { exam_code: "sca" } });

  // The admin sets the institution up the way the console would.
  const admin = await switchWorkspace(await login(accounts.admin.email, PASSWORD), slug);
  const programme = await call(admin, `/api/v1/orgs/${slug}/programmes`, { method: "POST", body: { exam_code: "sca" } });
  await call(admin, `/api/v1/orgs/${slug}/programmes/${programme.id}`, { method: "PATCH", body: { status: "active" } });
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
