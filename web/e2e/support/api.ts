/**
 * API seams for the end-to-end specs: the same calls scripts/seed-demo-org.mjs
 * makes, used to put a world in place that the browser then drives. Only ever
 * talks to the local platform-api (global-setup refuses anything else).
 */
import { signInWithPassword } from "../../scripts/admin-totp.mjs";
import { ACCOUNT, API, WEB } from "../../.claude/skills/verify/harness.mjs";
import { appendFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";

export { API, WEB };
export const PASSWORD = "e2e-correct-horse-1";
/** The seeded platform admin: the verify harness account. */
export const ADMIN = ACCOUNT;

export function assertLocalApi(): void {
  const host = new URL(API).hostname;
  if (!["localhost", "127.0.0.1", "::1", "[::1]"].includes(host)) {
    throw new Error(`e2e writes data; refusing to run against ${API}. Set VERIFY_API_URL to a local platform-api.`);
  }
}

export class ApiError extends Error {
  status: number;
  code: string | undefined;
  constructor(status: number, code: string | undefined, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function call<T = Record<string, unknown>>(
  token: string | null,
  path: string,
  init: { method?: string; body?: unknown } = {},
): Promise<T> {
  assertLocalApi();
  const response = await fetch(`${API}${path}`, {
    method: init.method ?? "GET",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new ApiError(response.status, payload?.code, `${init.method ?? "GET"} ${path} -> ${response.status} ${payload?.code ?? ""} ${payload?.message ?? ""}`);
  }
  return payload as T;
}

export async function login(email: string, password: string): Promise<string> {
  return (await loginPatiently(email, password)).access_token;
}

/** `/api/v1/orgs/<slug><tail>`; `tail` starts with a slash. */
export const orgPath = (slug: string, tail = "") => `/api/v1/orgs/${slug}${tail}`;

/**
 * Register, waiting out the api's per-address sign-up limit (a 429, 8 attempts 30s apart: other specs share it)
 * and tolerating an address that already exists (409), so a re-seed with a saved account works.
 */
export async function register(email: string, name: string): Promise<void> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      await call(null, "/api/v1/auth/register", { method: "POST", body: { email, password: PASSWORD, name } });
      return;
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) return;
      if (attempt >= 7 || !(error instanceof ApiError) || error.status !== 429) throw error;
      await new Promise((resolve) => setTimeout(resolve, 30_000));
    }
  }
}

export interface SeededOrg {
  slug: string;
  token: string;
  account: { email: string; password: string };
}

/** This run's ledger of created organisations (one slug per line); global-teardown deletes them. Scoped by E2E_RUN_ID so concurrent runs never delete each other's. */
export const orgsFile = () => join(process.cwd(), "e2e", ".auth", `orgs-${process.env.E2E_RUN_ID}.txt`);

/** Create an organisation as the platform admin, recording its slug first so a half-built one is swept too. Every spec creates organisations through this. */
export async function createPlatformOrg(slug: string, name: string, orgType: string): Promise<string> {
  mkdirSync(dirname(orgsFile()), { recursive: true });
  appendFileSync(orgsFile(), `${slug}\n`);
  const platform = await login(ADMIN.email, ADMIN.password);
  await call(platform, "/api/v1/platform/organizations", { method: "POST", body: { name, slug, org_type: orgType } });
  return platform;
}

/**
 * A fresh institution "St Mary's Medical School" (slug `<prefix>-<stamp>`) with its signed-in admin as `role`.
 * The admin's address is unique per run unless `email` is given (a saved account being re-seeded).
 */
export async function createOrg(options: { prefix: string; role: "owner" | "institution_admin" | "partner_admin"; adminName: string; email?: string; orgType?: "institution" | "employer" | "partner"; orgName?: string }): Promise<SeededOrg> {
  const id = stamp();
  const slug = `${options.prefix}-${id}`;
  const account = { email: options.email ?? `${options.prefix}-admin-${id}@example.com`, password: PASSWORD };
  const platform = await createPlatformOrg(slug, options.orgName ?? "St Mary's Medical School", options.orgType ?? "institution");
  await register(account.email, options.adminName);
  await call(platform, `/api/v1/platform/organizations/${slug}/memberships`, { method: "POST", body: { email: account.email, role: options.role } });
  const token = await switchWorkspace(await login(account.email, PASSWORD), slug);
  return { slug, token, account };
}

export async function switchWorkspace(token: string, orgSlug: string): Promise<string> {
  return (await call(token, "/api/v1/auth/switch-workspace", { method: "POST", body: { org_slug: orgSlug } })).access_token as string;
}

export const stamp = () => Date.now().toString(36);

/** Sign in, waiting out the api's sign-in rate limit (10 a minute) instead of failing on it. */
export async function loginPatiently(email: string, password: string): Promise<Session> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return (await signInWithPassword(API, email, password)) as Session;
    } catch (error) {
      if (attempt >= 6 || !String((error as Error).message).includes("429")) throw error;
      await new Promise((resolve) => setTimeout(resolve, 15_000));
    }
  }
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}
