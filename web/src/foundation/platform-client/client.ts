import {
  PlatformError,
  PlatformTransportError,
  type PlatformErrorBody,
} from "@/foundation/platform-client/errors";

/**
 * The unified platform API client.
 *
 * One backend replaces b2b-api and b2c-api, so there is one client rather
 * than B2B's axios layer plus B2C's ~120 inline `axiosInstance` calls. Built
 * on `fetch` deliberately: the axios instances carry interceptors tied to the
 * old auth and base URLs, and inheriting those would couple the switchover to
 * the thing it replaces.
 *
 * Nothing imports this yet. Domains move over one at a time behind
 * `@/foundation/platform-client/flags`.
 */

export function platformApiUrl(): string {
  const raw =
    process.env.NEXT_PUBLIC_PLATFORM_API_URL?.trim() || "http://127.0.0.1:8002";
  return raw.replace(/\/+$/, "");
}

type TokenSource = () => string | null | Promise<string | null>;

let readToken: TokenSource = () => null;

/**
 * Supply the access token.
 *
 * Set once where auth lives, rather than each call site reaching for storage —
 * that spread is what made B2C's `app_type` ambient client state.
 */
export function setPlatformTokenSource(source: TokenSource): void {
  readToken = source;
}

export interface RequestOptions {
  method?: string;
  /** Serialised as JSON. Use `formData` for uploads. */
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | null | undefined>;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  /**
   * Sent as `Idempotency-Key`, so a repeated POST can be one action.
   *
   * This is where the supervisor console's module-level
   * `mockAgentDispatchLock` Set belongs — a React StrictMode double-render is
   * not a second dispatch, and a module-level Set does not survive a reload.
   *
   * No endpoint reads the header yet: the backend derives its idempotency keys
   * internally (`signoff:{sitting}:{trainee}:{revision}`). Sending it costs
   * nothing and means the client does not change when a route honours it.
   */
  idempotencyKey?: string;
}

function withQuery(path: string, query: RequestOptions["query"]): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null) params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

function asErrorBody(status: number, payload: unknown): PlatformErrorBody {
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (typeof obj.code === "string" && typeof obj.message === "string") {
      return obj as unknown as PlatformErrorBody;
    }
  }
  // A proxy, a gateway or a crash before the app's error handler ran. Shaped
  // like an `ErrorResponse` so callers have one thing to handle, and given a
  // code that exists so the union stays honest.
  return {
    code: "internal_error",
    message: `Request failed (${status})`,
  };
}

export async function platformRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, formData, query, signal, idempotencyKey } = options;

  const headers: Record<string, string> = { Accept: "application/json", ...options.headers };
  const token = await readToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  // FormData sets its own multipart boundary; setting Content-Type breaks it.
  if (body !== undefined && !formData) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${platformApiUrl()}${withQuery(path, query)}`, {
      method,
      headers,
      signal,
      credentials: "omit",
      body: formData ?? (body === undefined ? undefined : JSON.stringify(body)),
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new PlatformTransportError("Could not reach the server", cause);
  }

  if (response.status === 204) return undefined as T;

  const raw = await response.text();
  let payload: unknown = null;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  }

  if (!response.ok) throw new PlatformError(response.status, asErrorBody(response.status, payload));
  return payload as T;
}
