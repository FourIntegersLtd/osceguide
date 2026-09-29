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
  // Browser: always same-origin `/api/v1` (proxied in dev — see next.config.ts).
  // `NEXT_PUBLIC_PLATFORM_API_URL` is for SSR and tooling only; using it in the
  // browser crosses origins (e.g. :3100 → :8002) and breaks sign-in when CORS
  // is not configured for the dev port.
  if (typeof window !== "undefined") return "";
  const explicit = process.env.NEXT_PUBLIC_PLATFORM_API_URL?.trim();
  if (explicit) return explicit.replace(/\/+$/, "");
  const server =
    process.env.PLATFORM_API_URL?.trim() || process.env.NEXT_PUBLIC_PLATFORM_API_URL?.trim();
  return (server || "http://127.0.0.1:8002").replace(/\/+$/, "");
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

function apiUnreachableDevMessage(status: number): string {
  return (
    `Request failed (${status}) — platform-api was not reached. ` +
    "Use http://localhost:3100 (not :3000). " +
    "Start the API: cd backend/platform-api && make start. " +
    "In platform-web/.env.local set PLATFORM_API_URL=http://127.0.0.1:8002 and restart npm run dev:webpack."
  );
}

function apiUnreachableMessage(status: number): string | null {
  if (process.env.NODE_ENV !== "development") return null;
  if (status === 404 || status === 500 || status === 502 || status === 503) {
    return apiUnreachableDevMessage(status);
  }
  return null;
}

function asErrorBody(status: number, payload: unknown): PlatformErrorBody {
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (typeof obj.code === "string" && typeof obj.message === "string") {
      return obj as unknown as PlatformErrorBody;
    }
    const unreachable = apiUnreachableMessage(status);
    if (unreachable) {
      return { code: "internal_error", message: unreachable };
    }
  }
  const unreachable = apiUnreachableMessage(status);
  if (unreachable) {
    return { code: "internal_error", message: unreachable };
  }
  // A proxy, a gateway or a crash before the app's error handler ran. Shaped
  // like an `ErrorResponse` so callers have one thing to handle, and given a
  // code that exists so the union stays honest.
  return {
    code: "internal_error",
    message: `Request failed (${status})`,
  };
}

export interface PlatformDownload {
  blob: Blob;
  filename: string;
}

async function platformFetch(
  path: string,
  options: RequestOptions,
  accept: string,
): Promise<Response> {
  const { method = "GET", body, formData, query, signal, idempotencyKey } = options;

  const headers: Record<string, string> = { Accept: accept, ...options.headers };
  const token = await readToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  // FormData sets its own multipart boundary; setting Content-Type breaks it.
  if (body !== undefined && !formData) headers["Content-Type"] = "application/json";

  try {
    return await fetch(`${platformApiUrl()}${withQuery(path, query)}`, {
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
}

async function readPayload(response: Response): Promise<unknown> {
  const raw = await response.text();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

export async function platformRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const response = await platformFetch(path, options, "application/json");
  if (response.status === 204) return undefined as T;

  const payload = await readPayload(response);
  if (!response.ok) throw new PlatformError(response.status, asErrorBody(response.status, payload));
  return payload as T;
}

/**
 * A file download that uses the same token and the same error mapping as
 * `platformRequest`. The filename is the one the response asks the browser to
 * save, from `Content-Disposition`.
 */
export async function platformDownload(
  path: string,
  options: RequestOptions = {},
): Promise<PlatformDownload> {
  const response = await platformFetch(path, options, "*/*");
  if (!response.ok) {
    const payload = await readPayload(response);
    throw new PlatformError(response.status, asErrorBody(response.status, payload));
  }
  return {
    blob: await response.blob(),
    filename: filenameFromContentDisposition(response.headers.get("Content-Disposition")),
  };
}

function filenameFromContentDisposition(header: string | null): string {
  if (!header) return "download";
  const encoded = /filename\*=(?:UTF-8''|utf-8'')([^;]+)/i.exec(header);
  if (encoded?.[1]) {
    try {
      return decodeURIComponent(encoded[1].trim().replace(/^"|"$/g, ""));
    } catch {
      // A malformed encoding falls through to the plain filename parameter.
    }
  }
  const quoted = /filename="([^"]*)"/.exec(header);
  if (quoted?.[1]) return quoted[1];
  const plain = /filename=([^;]+)/.exec(header);
  return plain?.[1]?.trim() ?? "download";
}

/** Hand a blob to the browser as a saved file, then drop the object URL. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
