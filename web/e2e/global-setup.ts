import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { ADMIN, API, assertLocalApi, call, login, orgPath, PASSWORD, register, stamp, switchWorkspace } from "./support/api";
import { ensureScaPlanOnSale } from "./support/db";
import { ensureTitledStations } from "./support/seed-sittings";
import { stagingWorld } from "./support/staging";
import { WORLD_FILE, type Role, type World } from "./support/world";

function writeWorld(built: World): void {
  mkdirSync(dirname(WORLD_FILE), { recursive: true });
  writeFileSync(WORLD_FILE, JSON.stringify(built, null, 2));
}

/**
 * The stations every run sits: ours by title, never whatever a dev database happens to list first
 * (a leftover station without the SCA template blocks has an empty brief: ASSESS-2).
 */
const LIBRARY_TITLES = ["E2E library station 1", "E2E library station 2", "E2E library station 3"];

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
  const programme = await call(admin, orgPath(slug, `/programmes`), { method: "POST", body: { exam_code: "sca" } });
  await call(admin, orgPath(slug, `/programmes/${programme.id}`), { method: "PATCH", body: { status: "active" } });
  // The setup guide counts a template only once the organisation holds its own copy of one.
  const platformTemplates = (await call(platform, "/api/v1/platform/station-templates?exam_code=sca&published_only=true")).items as {
    id: string;
    exam_code: string | null;
  }[];
  const scaTemplate = platformTemplates.find((t) => t.exam_code === "sca");
  if (!scaTemplate) throw new Error("no published SCA station template: run scripts/seed_station_templates.py --apply");
  await call(admin, orgPath(slug, `/station-templates/${scaTemplate.id}/copy`), { method: "POST" });
  const trainee = await call(admin, orgPath(slug, `/trainees`), {
    method: "POST",
    body: { email: accounts.trainee.email, first_name: "Tess", last_name: "Trainee" },
  });
  const stationVersionIds = await ensureTitledStations(LIBRARY_TITLES);
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
