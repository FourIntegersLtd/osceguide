import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { ADMIN, API, assertLocalApi, call, login, PASSWORD, register, stamp, switchWorkspace } from "./support/api";
import { WORLD_FILE, type Role, type World } from "./support/world";

export default async function globalSetup(): Promise<void> {
  // Before anything writes: the specs create organisations and accounts.
  assertLocalApi();
  const health = await fetch(`${API}/health`).catch(() => null);
  if (!health?.ok) throw new Error(`platform-api is not answering at ${API}. Start it first (docs/CORE-JOURNEYS.md).`);

  const id = stamp();
  const slug = `e2e-${id}`;
  const orgName = `E2E Institute ${id}`;
  const accounts: World["accounts"] = {
    admin: { email: `e2e-admin-${id}@example.com`, name: "Ada Admin" },
    supervisor: { email: `e2e-sup-${id}@example.com`, name: "Sam Supervisor" },
    trainee: { email: `e2e-trainee-${id}@example.com`, name: "Tess Trainee" },
    consumer: { email: `e2e-learner-${id}@example.com`, name: "Lena Learner" },
    newcomer: { email: `e2e-newcomer-${id}@example.com`, name: "Nia Newcomer" },
  };
  const roles: Partial<Record<Role, string>> = {
    admin: "institution_admin",
    supervisor: "supervisor",
    trainee: "trainee",
  };

  const platform = await login(ADMIN.email, ADMIN.password);
  await call(platform, "/api/v1/platform/organizations", {
    method: "POST",
    body: { name: orgName, slug, org_type: "institution" },
  });
  for (const role of Object.keys(accounts) as Role[]) {
    await register(accounts[role].email, accounts[role].name);
    const orgRole = roles[role];
    if (!orgRole) continue;
    await call(platform, `/api/v1/platform/organizations/${slug}/memberships`, {
      method: "POST",
      body: { email: accounts[role].email, role: orgRole },
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
  const library = await call(admin, "/api/v1/stations?exam_code=sca&limit=3");
  const stationVersionIds = (library.items as { version_id: string }[]).map((item) => item.version_id);
  if (stationVersionIds.length === 0) throw new Error("no published SCA stations: run scripts/seed_platform.py");

  const built: World = {
    slug,
    orgName,
    accounts,
    traineeUserId: trainee.user_id as string,
    programmeId: programme.id as string,
    stationVersionIds,
  };
  mkdirSync(dirname(WORLD_FILE), { recursive: true });
  writeFileSync(WORLD_FILE, JSON.stringify(built, null, 2));
  console.log(`e2e world: org ${slug} on ${API}`);
}
