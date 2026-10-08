/**
 * API seams for the end-to-end specs: the same calls scripts/seed-demo-org.mjs
 * makes, used to put a world in place that the browser then drives. Only ever
 * talks to the local platform-api (global-setup refuses anything else).
 */
import { signInWithPassword } from "../../scripts/admin-totp.mjs";
import { ACCOUNT, API, WEB } from "../../.claude/skills/verify/harness.mjs";

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

export async function register(email: string, name: string): Promise<void> {
  await call(null, "/api/v1/auth/register", { method: "POST", body: { email, password: PASSWORD, name } });
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
