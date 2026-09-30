/**
 * Retire junk from the local platform station library (archive published rows).
 *
 * Published stations cannot be deleted — same rule as production — but archiving
 * removes them from the authoring catalogue and the public library index.
 *
 *   node scripts/clean-dev-library.mjs --dev --title "Hip pain in a runner"
 *   node scripts/clean-dev-library.mjs --dev --dry-run
 *
 * Flags (combine as needed):
 *   --dev              titles starting with "Dev ·" (from seed-dev-stations.mjs)
 *   --title <exact>    every published station with this title (repeatable)
 *   --title-prefix <p> titles starting with this prefix (repeatable)
 *   --dry-run          print matches without archiving
 */

import { signInWithPassword } from "./admin-totp.mjs";

const API = process.env.PLATFORM_API_URL ?? "http://127.0.0.1:8002";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : fallback;
}

function flag(name) {
  return process.argv.includes(`--${name}`);
}

function repeatedFlag(name) {
  const out = [];
  for (let i = 0; i < process.argv.length; i += 1) {
    if (process.argv[i] === `--${name}` && process.argv[i + 1]) {
      out.push(process.argv[i + 1]);
      i += 1;
    }
  }
  return out;
}

const EMAIL = arg("email", "dev@example.com");
const PASSWORD = arg("password", "platform-dev-password-1");
const DRY = flag("dry-run");
const DEV_PREFIX = flag("dev");

const titles = repeatedFlag("title");
const titlePrefixes = repeatedFlag("title-prefix");

if (!DEV_PREFIX && titles.length === 0 && titlePrefixes.length === 0) {
  console.error("Pass --dev, --title \"…\", and/or --title-prefix \"…\"");
  process.exit(1);
}

async function call(path, { method = "GET", body, token } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  const parsed = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(`${method} ${path} → ${response.status} ${text.slice(0, 240)}`);
  }
  return parsed;
}

function matches(row) {
  if (row.status !== "published") return false;
  if (DEV_PREFIX && row.title.startsWith("Dev ·")) return true;
  if (titles.includes(row.title)) return true;
  if (titlePrefixes.some((prefix) => row.title.startsWith(prefix))) return true;
  return false;
}

async function allPlatformStations(token) {
  const out = [];
  let cursor = null;
  for (;;) {
    const query = new URLSearchParams({ limit: "100" });
    if (cursor) query.set("cursor", cursor);
    const page = await call(`/api/v1/platform/stations?${query}`, { token });
    out.push(...(page.items ?? []));
    if (!page.next_cursor) break;
    cursor = page.next_cursor;
  }
  return out;
}

async function main() {
  const auth = await signInWithPassword(API, EMAIL, PASSWORD);
  const token = auth.access_token;
  const rows = (await allPlatformStations(token)).filter(matches);

  if (rows.length === 0) {
    console.log("Nothing to archive.");
    return;
  }

  for (const row of rows) {
    const label = `${row.title} (${row.id.slice(0, 6)}… · ${row.exam_code} v${row.version})`;
    if (DRY) {
      console.log(`would archive ${label}`);
      continue;
    }
    await call(`/api/v1/platform/stations/${row.id}/versions/${row.version}/archive`, {
      method: "POST",
      token,
    });
    console.log(`archived ${label}`);
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
