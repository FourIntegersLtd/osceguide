/**
 * A worked institution, built entirely through the public API.
 *
 * Gives a fresh database something to sign into: an organisation with staff,
 * trainees, a programme, a sitting and a
 * circuit ready to run. Every call is one the console makes, so this doubles
 * as an end-to-end check of the Assess path.
 *
 * Idempotent: an organisation whose slug exists is reused, and each step
 * tolerates what is already there.
 *
 *   node scripts/seed-demo-org.mjs --email dev@example.com --password ...
 */
const API = process.env.PLATFORM_API_URL ?? "http://127.0.0.1:8002";
const SLUG = "st-marys";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
}

let token = null;

async function call(path, { method = "GET", body, allow = [] } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    if (allow.includes(payload?.code)) return null;
    throw new Error(`${method} ${path} -> ${response.status} ${payload?.code ?? ""} ${payload?.message ?? ""}`);
  }
  return payload;
}

const say = (message) => console.log(message);

async function main() {
  const email = arg("email", "dev@example.com");
  const password = arg("password", "platform-dev-password-1");

  token = (await call("/api/v1/auth/login", { method: "POST", body: { email, password } })).access_token;

  // 1. The organisation. `institution` is what decides which console its
  //    members land in; an employer would be the same call with `employer`.
  const orgs = await call("/api/v1/platform/organizations?limit=100");
  let org = orgs.items.find((item) => item.slug === SLUG);
  if (!org) {
    org = await call("/api/v1/platform/organizations", {
      method: "POST",
      body: { name: "St Mary's", slug: SLUG, org_type: "institution" },
    });
    say(`created organisation ${org.slug}`);
  } else {
    say(`organisation ${org.slug} already exists`);
  }

  // 2. Make the signed-in account an admin of it, so there is something to open.
  await call(`/api/v1/platform/organizations/${SLUG}/memberships`, {
    method: "POST",
    body: { email, role: "institution_admin" },
    allow: ["membership_exists", "already_member", "conflict"],
  });
  say(`${email} is an institution admin of ${SLUG}`);

  // The platform token carries the active membership, so it has to be re-minted
  // before any org-scoped call will be authorised.
  const switched = await call("/api/v1/auth/switch-workspace", {
    method: "POST",
    body: { org_slug: SLUG },
  });
  token = switched.access_token;

  // 3. A programme: this institution runs SCA.
  await call(`/api/v1/orgs/${SLUG}/programmes`, {
    method: "POST",
    body: { exam_code: "sca" },
    allow: ["programme_exists", "conflict"],
  });
  say("programme: sca");

  // 4. Trainees.
  const people = [
    { email: "amara.okafor@example.com", first_name: "Amara", last_name: "Okafor" },
    { email: "tom.reilly@example.com", first_name: "Tom", last_name: "Reilly" },
    { email: "sana.iqbal@example.com", first_name: "Sana", last_name: "Iqbal" },
  ];
  const TRAINEE_PASSWORD = "platform-dev-password-1";
  const existing = await call(`/api/v1/orgs/${SLUG}/trainees?limit=100`);
  const have = new Set(existing.items.map((t) => t.email));
  for (const person of people) {
    if (have.has(person.email)) continue;
    await call(`/api/v1/orgs/${SLUG}/trainees`, { method: "POST", body: person, allow: ["trainee_exists"] });
  }
  // A circuit slot names a *user*, not a roster row: `trainee_ids` on the wire
  // is a list of user ids, and a trainee who has never signed in has no user
  // to name. So each demo trainee gets an account, which is also what makes
  // them able to open their own portal.
  const admin = token;
  for (const person of people) {
    token = null;
    await call("/api/v1/auth/register", {
      method: "POST",
      body: {
        email: person.email,
        password: TRAINEE_PASSWORD,
        name: `${person.first_name} ${person.last_name}`,
      },
      allow: ["email_taken", "email_exists", "conflict"],
    });
  }
  token = admin;

  const trainees = await call(`/api/v1/orgs/${SLUG}/trainees?limit=100`);
  const rosterable = trainees.items.filter((t) => t.user_id !== null);
  say(`${trainees.items.length} trainees, ${rosterable.length} with accounts`);

  const programmes = await call(`/api/v1/orgs/${SLUG}/programmes?limit=20`);
  const programme = programmes.items.find((p) => p.exam_code === "sca");
  if (!programme) throw new Error("no sca programme — run step 3");

  // 5. A sitting, and a circuit on it.
  const sittings = await call(`/api/v1/orgs/${SLUG}/sittings?limit=50`);
  let sitting = sittings.items.find((item) => item.name === "March mock OSCE");
  if (!sitting) {
    sitting = await call(`/api/v1/orgs/${SLUG}/sittings`, {
      method: "POST",
      body: {
        name: "March mock OSCE",
        mode: "training",
        sitting_type: "group_training",
        programme_id: programme.id,
        scheduled_for: new Date(Date.now() + 86_400_000).toISOString(),
      },
    });
    say("created sitting");
  }

  if ((sitting.circuits ?? []).length === 0) {
    const library = await call("/api/v1/stations?exam_code=sca&limit=10");
    const stationVersionIds = library.items.slice(0, 3).map((s) => s.version_id);
    if (stationVersionIds.length === 0) throw new Error("no published stations in the library");
    if (rosterable.length === 0) throw new Error("no trainee has an account yet");
    await call(`/api/v1/orgs/${SLUG}/sittings/${sitting.id}/circuits`, {
      method: "POST",
      body: {
        name: "Morning circuit",
        station_version_ids: stationVersionIds,
        trainee_ids: rosterable.slice(0, 3).map((t) => t.user_id),
        timing: { reading_minutes: 2, simulation_minutes: 10 },
      },
    });
    say("created circuit");
  } else {
    say("circuit already exists");
  }

  say(`\nOpen http://localhost:3100/assess/${SLUG} as ${email}`);
  say(`A trainee's view: http://localhost:3100/assess/trainee as ${people[0].email}`);
}

main().catch((error) => {
  console.error("\n" + error.message);
  process.exit(1);
});
