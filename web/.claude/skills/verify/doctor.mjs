/**
 * Read-only preflight for the verify skill. Answers "can a browser run start
 * now?" and says which step to fix when it cannot. Changes nothing.
 *
 *   node .claude/skills/verify/doctor.mjs
 */
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { signInWithPassword } from "../../../scripts/admin-totp.mjs";
import { API, WEB, ACCOUNT } from "./harness.mjs";

const CHROME = process.env.VERIFY_CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const checks = [];

async function status(url) {
  try {
    const res = await fetch(url, { redirect: "manual", signal: AbortSignal.timeout(90_000) });
    return res.status;
  } catch {
    return 0;
  }
}

function listener(port) {
  try {
    return execFileSync("lsof", ["-nP", `-iTCP:${port}`, "-sTCP:LISTEN", "-Fpc"], { encoding: "utf8" })
      .split("\n")
      .filter((l) => l.startsWith("c"))
      .map((l) => l.slice(1))
      .join(",");
  } catch {
    return "";
  }
}

function check(name, ok, fix) {
  checks.push({ name, ok, fix });
}

check("system Chrome present", existsSync(CHROME), `install Chrome or set VERIFY_CHROME`);
check("docker postgres :5433", Boolean(listener(5433)), "cd ../api && make db-up");

const health = await status(`${API}/health`);
check(
  `platform-api ${API}/health -> ${health === 0 ? "no answer" : health}`,
  health === 200,
  `nothing healthy at ${API} (from VERIFY_API_URL, default http://127.0.0.1:8002). Start it with "cd ../api && make start", or if it runs on another port set VERIFY_API_URL to it`,
);

// The first request compiles /login, which takes ~15s on webpack dev.
const login = await status(`${WEB}/login`);
check(`platform-web ${WEB}/login -> ${login}`, login === 200, "npm run dev (`npm run dev:webpack` only if Turbopack panics)");

if (health === 200) {
  let signedIn = false;
  let detail = "no answer";
  try {
    const session = await signInWithPassword(API, ACCOUNT.email, ACCOUNT.password);
    signedIn = Boolean(session.access_token);
    detail = signedIn ? "200" : "no token";
  } catch (error) {
    detail = error.message;
  }
  check(
    `test account ${ACCOUNT.email} signs in -> ${detail}`,
    signedIn,
    "a fresh database is empty: run scripts/seed_platform.py, then bootstrap the account with ADMIN_TOTP_SECRET set (see SKILL.md Launch)",
  );
}

for (const c of checks) console.log(`${c.ok ? "ok  " : "FAIL"} ${c.name}${c.ok ? "" : `\n     fix: ${c.fix}`}`);
const failed = checks.filter((c) => !c.ok).length;
console.log(failed ? `\n${failed} check(s) failed` : "\nready");
process.exitCode = failed ? 1 : 0;
