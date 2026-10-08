import {
  PlatformError,
  PlatformTransportError,
  type PlatformErrorBody,
} from "@/foundation/platform-client/errors";
import { noteOrgRefusal } from "@/foundation/platform-client/orgSuspension";
import { createSseParser, type SseFrame } from "@/foundation/platform-client/sse";

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

let onUnauthorized: (() => void) | null = null;

/**
 * Be told when the API refuses a token this client sent (a 401 anywhere but sign-in), so the
 * session can re-check itself instead of leaving each screen to show its own error. Set where
 * the session lives; `null` removes it.
 */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

export interface RequestOptions {
  method?: string;
  /** Serialised as JSON. Use `formData` for uploads. */
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | readonly string[] | null | undefined>;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  /**
   * Sent as `Idempotency-Key`, so a repeated POST can be one action.
   *
   * This is where the supervisor console's module-level
   * `mockAgentDispatchLock` Set belongs — a React StrictMode double-render is
   * not a second dispatch, and a module-level Set does not survive a reload.
   *
   * Only `POST /billing/checkout` reads it so far (passed to Stripe, scoped to the buyer); the
   * rest derive their keys internally (`signoff:{sitting}:{trainee}:{revision}`). Sending it
   * elsewhere costs nothing and means the client does not change when a route honours it.
   */
  idempotencyKey?: string;
}

function withQuery(path: string, query: RequestOptions["query"]): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    // A list-typed query param (e.g. `version_ids`) is repeated, not
    // comma-joined: FastAPI's `Query(...)` over a `list[...]` reads
    // `?k=a&k=b`, and a single `k=a,b` value arrives as one unparsed string.
    if (Array.isArray(value)) {
      for (const item of value) params.append(key, String(item));
    } else {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

function apiUnreachableDevMessage(status: number): string {
  return (
    `Request failed (${status}). The API was not reached. ` +
    "Use http://localhost:3100 (not :3000). " +
    "Start the API: cd api && make start. " +
    "In web/.env.local set PLATFORM_API_URL=http://127.0.0.1:8002 and restart npm run dev:webpack."
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
  // A proxy, a gateway, the framework's own 404/405 or a crash before the app's
  // error handler ran. Shaped like an `ErrorResponse` so callers have one thing
  // to handle, and given a code that exists so the union stays honest. The
  // message is read by people, so it says what happened, not the status code.
  return { code: "internal_error", message: fallbackMessage(status) };
}

function fallbackMessage(status: number): string {
  if (status === 404 || status === 405) return "That action isn't available here.";
  if (status >= 500) return "Something went wrong on our side. Try again.";
  return "Something went wrong. Try again.";
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

  const url = `${platformApiUrl()}${withQuery(path, query)}`;
  const init: RequestInit = {
    method,
    headers,
    signal,
    credentials: "omit",
    body: formData ?? (body === undefined ? undefined : JSON.stringify(body)),
  };
  // Only a read is asked twice: repeating a write the server may already have
  // done is not this layer's call.
  const retries = method === "GET" ? GATEWAY_RETRY_DELAYS_MS : [];

  for (let attempt = 0; ; attempt += 1) {
    const last = attempt >= retries.length;
    try {
      const response = await fetch(url, init);
      if (last || !GATEWAY_STATUSES.has(response.status)) {
        // Sign-in and the other /auth routes answer 401 for a wrong password or code, which says
        // nothing about a session; and with no token sent there was no session to lose.
        if (response.status === 401 && token && !path.startsWith("/api/v1/auth/")) onUnauthorized?.();
        return response;
      }
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
      if (last) throw new PlatformTransportError("Could not reach the server", cause);
    }
    await pause(retries[attempt] ?? 0, signal);
  }
}

/**
 * A gateway in front of platform-api answering for it: Railway while a deploy
 * swaps containers, Vercel's rewrite when the upstream connection drops. They
 * say nothing about the request, so a read is asked again, twice, before the
 * caller sees the failure (staging, 2026-10-03: a dozen 502s on `/me` during a
 * deploy left a screen on its spinner).
 */
const GATEWAY_STATUSES = new Set([502, 503, 504]);
const GATEWAY_RETRY_DELAYS_MS = [400, 1_200];

function pause(ms: number, signal: AbortSignal | undefined): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

/** The error a refused request throws; an organisation's suspension is noted on the way. */
function refusal(path: string, status: number, payload: unknown): PlatformError {
  const error = new PlatformError(status, asErrorBody(status, payload));
  noteOrgRefusal(path, error.code);
  return error;
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
  if (!response.ok) throw refusal(path, response.status, payload);
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
    throw refusal(path, response.status, payload);
  }
  return {
    blob: await response.blob(),
    filename: filenameFromContentDisposition(response.headers.get("Content-Disposition")),
  };
}

/**
 * A POST (or any method) whose answer is a Server-Sent Events stream.
 *
 * `EventSource` cannot send a body or an Authorization header, so a stream
 * that starts from a request body — a rubric trial mark — is read here with
 * `fetch`, carrying the same token and the same error mapping as
 * `platformRequest`. A refusal before the stream opens (422, 429, 503) throws a
 * `PlatformError` exactly as a JSON call would. Each finished frame is handed
 * to `onFrame` as it arrives; the promise settles when the server closes the
 * stream. Abort `options.signal` to stop reading.
 */
export async function platformStream(
  path: string,
  options: RequestOptions,
  onFrame: (frame: SseFrame) => void,
): Promise<void> {
  const response = await platformFetch(path, options, "text/event-stream");
  if (!response.ok) {
    const payload = await readPayload(response);
    throw refusal(path, response.status, payload);
  }
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = createSseParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const frame of parser.push(decoder.decode(value, { stream: true }))) onFrame(frame);
    }
    for (const frame of parser.push(`${decoder.decode()}\n\n`)) onFrame(frame);
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new PlatformTransportError("The stream was cut off", cause);
  } finally {
    reader.releaseLock();
  }
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
