/**
 * Demo study material, through the public API.
 *
 * Not a fixture and not a migration: it posts what a platform admin would post,
 * so it exercises the same routes the console will. Idempotent by title — a
 * second run publishes nothing new.
 *
 *   node scripts/seed-dev-content.mjs --email dev@example.com --password ...
 */
const API = process.env.PLATFORM_API_URL ?? "http://127.0.0.1:8002";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
}

async function call(path, { method = "GET", body, token } = {}) {
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
    throw new Error(`${method} ${path} -> ${response.status} ${payload?.code ?? ""} ${payload?.message ?? ""}`);
  }
  return payload;
}

const ITEMS = [
  {
    kind: "summary",
    exam_code: "sca",
    title: "Safety netting that actually lands",
    summary: "What to say, when to say it, and how examiners hear it.",
    content: {
      body_md:
        "## Why it is marked\n\nSafety netting is scored because it is the part of the consultation that protects the patient after they leave.\n\n### A workable shape\n\n1. Name what you expect to happen.\n2. Name what would worry you.\n3. Say exactly what to do, and by when.\n\n> \"I'd expect this to settle over a week. If the pain wakes you at night, or you get a fever, ring the surgery the same day.\"",
    },
  },
  {
    kind: "slide_deck",
    exam_code: "sca",
    title: "Opening the consultation",
    summary: "Six slides on the first ninety seconds.",
    content: {
      slides: [
        { title: "The first ninety seconds", body: "More marks turn on the opening than candidates expect." },
        { title: "Signpost early", body: "Tell the patient what the next few minutes will look like." },
        { title: "One open question", body: "Ask it, then stop talking. Silence is doing work." },
        { title: "Listen for the cue", body: "The reason they came is rarely the first thing they say." },
        { title: "Check, do not assume", body: "Reflect back what you heard before moving on." },
        { title: "Agree the agenda", body: "Name what you will cover, and ask what you have missed." },
      ],
    },
  },
];

async function main() {
  const email = arg("email", "dev@example.com");
  const password = arg("password", "platform-dev-password-1");

  const auth = await call("/api/v1/auth/login", {
    method: "POST",
    body: { email, password },
  });
  const token = auth.access_token;

  const existing = new Set(
    (await call("/api/v1/media?limit=100", { token })).items.map((item) => item.title),
  );

  for (const item of ITEMS) {
    if (existing.has(item.title)) {
      console.log(`skip   ${item.kind.padEnd(8)} ${item.title}`);
      continue;
    }
    const created = await call("/api/v1/media", { method: "POST", body: item, token });
    // Drafts are 404 to everyone but an admin, so publishing is the point.
    await call(`/api/v1/media/${created.id}/publish`, { method: "POST", token });
    console.log(`create ${item.kind.padEnd(8)} ${item.title}`);
  }

  const published = await call("/api/v1/media?limit=100", { token });
  console.log(`\n${published.items.length} published items`);
  console.log(
    "\nStudy bodies need a live entitlement (OpenAI alone does not unlock them).",
  );
  console.log(
    "From platform-api: make grant-exam-access EMAIL=" +
      email +
      " EXAM=sca",
  );
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
