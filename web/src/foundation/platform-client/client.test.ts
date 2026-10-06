import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import {
  platformDownload,
  platformRequest,
  setPlatformTokenSource,
} from "@/foundation/platform-client/client";
import { PlatformError, PlatformTransportError, hasCode } from "@/foundation/platform-client/errors";

const realFetch = globalThis.fetch;

function respondWith(status: number, body: string, contentType = "application/json") {
  globalThis.fetch = (async () =>
    new Response(status === 204 ? null : body, {
      status,
      headers: { "content-type": contentType },
    })) as typeof fetch;
}

afterEach(() => {
  globalThis.fetch = realFetch;
  setPlatformTokenSource(() => null);
});

test("an error keeps the code, the status and the request id", async () => {
  respondWith(
    403,
    JSON.stringify({
      code: "not_entitled",
      message: "You do not have access to this exam",
      details: { exam: "sca" },
      request_id: "req-42",
    }),
  );

  const err = await platformRequest("/api/v1/attempts", { method: "POST" }).then(
    () => null,
    (e: unknown) => e,
  );

  assert.ok(err instanceof PlatformError);
  assert.equal(err.code, "not_entitled");
  assert.equal(err.status, 403);
  assert.equal(err.requestId, "req-42");
  assert.deepEqual(err.details, { exam: "sca" });
  // The point of the whole layer: branch on the code, never on the prose.
  assert.ok(hasCode(err, "not_entitled"));
  assert.ok(!hasCode(err, "forbidden"));
});

test("a gateway error that outlasts the retries still has a code to switch on", async () => {
  respondWith(502, "<html>Bad Gateway</html>", "text/html");

  const err = await platformRequest("/api/v1/me").then(
    () => null,
    (e: unknown) => e,
  );

  assert.ok(err instanceof PlatformError);
  assert.equal(err.code, "internal_error");
  assert.equal(err.status, 502);
});

test("an unreachable server is a transport error, not an API error", async () => {
  globalThis.fetch = (async () => {
    throw new TypeError("network down");
  }) as typeof fetch;

  const err = await platformRequest("/api/v1/me").then(
    () => null,
    (e: unknown) => e,
  );

  // Retrying this is usually right; retrying a 409 usually is not, so the
  // caller must be able to tell them apart.
  assert.ok(err instanceof PlatformTransportError);
  assert.ok(!(err instanceof PlatformError));
});

test("a read that meets a gateway error mid-deploy is asked again and succeeds", async () => {
  const answers = [
    new Response("<html>Bad Gateway</html>", { status: 502 }),
    new Response("<html>Bad Gateway</html>", { status: 502 }),
    new Response(JSON.stringify({ id: "u1" }), { status: 200 }),
  ];
  let calls = 0;
  globalThis.fetch = (async () => answers[calls++]) as typeof fetch;

  assert.deepEqual(await platformRequest("/api/v1/me"), { id: "u1" });
  assert.equal(calls, 3);
});

test("a write is never repeated on a gateway error", async () => {
  let calls = 0;
  globalThis.fetch = (async () => {
    calls += 1;
    return new Response("<html>Bad Gateway</html>", { status: 502 });
  }) as typeof fetch;

  const err = await platformRequest("/api/v1/attempts", { method: "POST", body: {} }).then(
    () => null,
    (e: unknown) => e,
  );

  assert.ok(err instanceof PlatformError);
  assert.equal(err.status, 502);
  assert.equal(calls, 1);
});

test("an API refusal on a read is not retried", async () => {
  let calls = 0;
  globalThis.fetch = (async () => {
    calls += 1;
    return new Response(JSON.stringify({ code: "unauthenticated", message: "no" }), { status: 401 });
  }) as typeof fetch;

  await platformRequest("/api/v1/me").catch(() => null);
  assert.equal(calls, 1);
});

test("204 resolves rather than failing to parse an empty body", async () => {
  respondWith(204, "");
  assert.equal(await platformRequest("/api/v1/sessions/current", { method: "DELETE" }), undefined);
});

test("the token is attached from the source, not read at each call site", async () => {
  let seen: Headers | undefined;
  globalThis.fetch = (async (_url: unknown, init?: RequestInit) => {
    seen = new Headers(init?.headers);
    return new Response("{}", { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;

  setPlatformTokenSource(() => "tok-123");
  await platformRequest("/api/v1/me");

  assert.equal(seen?.get("authorization"), "Bearer tok-123");
});

test("an idempotency key travels as a header, ready for a route to honour it", async () => {
  let seen: Headers | undefined;
  globalThis.fetch = (async (_url: unknown, init?: RequestInit) => {
    seen = new Headers(init?.headers);
    return new Response("{}", { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;

  await platformRequest("/api/v1/circuits/c1/dispatch-agent", {
    method: "POST",
    idempotencyKey: "org:session:slot",
  });

  assert.equal(seen?.get("idempotency-key"), "org:session:slot");
});

test("a download keeps the filename from Content-Disposition and the error code", async () => {
  globalThis.fetch = (async () =>
    new Response("name,email\n", {
      status: 200,
      headers: {
        "content-type": "text/csv",
        "content-disposition": 'attachment; filename="finals-results.csv"',
      },
    })) as typeof fetch;

  const file = await platformDownload("/api/v1/orgs/kings/sittings/x/report.csv");
  assert.equal(file.filename, "finals-results.csv");
  assert.equal(await file.blob.text(), "name,email\n");

  globalThis.fetch = (async () =>
    new Response(
      JSON.stringify({ code: "result_not_released", message: "Your result has not been released yet" }),
      { status: 404, headers: { "content-type": "application/json" } },
    )) as typeof fetch;

  const err = await platformDownload("/api/v1/me/results/x.pdf").then(
    () => null,
    (cause: unknown) => cause,
  );
  assert.ok(err instanceof PlatformError);
  assert.equal(err.code, "result_not_released");
});

test("a 405 with FastAPI's own body reads as words, not a status code", async () => {
  respondWith(405, JSON.stringify({ detail: "Method Not Allowed" }));

  const err = await platformRequest("/api/v1/platform/exams/x", { method: "DELETE" }).then(
    () => null,
    (e: unknown) => e,
  );

  assert.ok(err instanceof PlatformError);
  assert.equal(err.status, 405);
  assert.equal(err.message, "That action isn't available here.");
});

test("a 500 with no body says the fault is ours, not a status code", async () => {
  respondWith(500, "");

  const err = await platformRequest("/api/v1/attempts", { method: "POST", body: {} }).then(
    () => null,
    (e: unknown) => e,
  );

  assert.ok(err instanceof PlatformError);
  assert.equal(err.status, 500);
  assert.equal(err.code, "internal_error");
  assert.equal(err.message, "Something went wrong on our side. Try again.");
});
