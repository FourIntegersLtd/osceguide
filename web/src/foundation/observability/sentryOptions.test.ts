import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { scrubEvent, sentryOptions } from "@/foundation/observability/sentryOptions";

describe("sentry options", () => {
  it("stays off without a DSN, so local and test runs send nothing", () => {
    assert.equal(sentryOptions("client", {}), null);
    assert.equal(sentryOptions("server", { SENTRY_DSN: "  " }), null);
  });

  it("gives the browser only the public DSN", () => {
    assert.equal(sentryOptions("client", { SENTRY_DSN: "https://server@x/1" }), null);
    assert.equal(
      sentryOptions("client", { NEXT_PUBLIC_SENTRY_DSN: "https://pub@x/1" })?.dsn,
      "https://pub@x/1",
    );
  });

  it("lets the server use its own DSN, falling back to the public one", () => {
    const env = { SENTRY_DSN: "https://server@x/1", NEXT_PUBLIC_SENTRY_DSN: "https://pub@x/1" };
    assert.equal(sentryOptions("server", env)?.dsn, "https://server@x/1");
    assert.equal(sentryOptions("server", { NEXT_PUBLIC_SENTRY_DSN: "https://pub@x/1" })?.dsn, "https://pub@x/1");
  });

  it("never sends personal data and samples traces", () => {
    const options = sentryOptions("client", {
      NEXT_PUBLIC_SENTRY_DSN: "https://pub@x/1",
      NEXT_PUBLIC_SENTRY_ENVIRONMENT: "staging",
    });
    assert.equal(options?.sendDefaultPii, false);
    assert.equal(options?.environment, "staging");
    assert.ok((options?.tracesSampleRate ?? 1) < 1);
  });

  it("drops credentials and bodies from a report's request", () => {
    const scrubbed = scrubEvent({
      request: {
        headers: { Authorization: "Bearer secret", cookie: "a=b", accept: "text/html" },
        cookies: { a: "b" },
        data: { password: "hunter2" },
      },
    });
    assert.deepEqual(scrubbed.request?.headers, { accept: "text/html" });
    assert.equal(scrubbed.request?.cookies, undefined);
    assert.equal(scrubbed.request?.data, undefined);
  });
});
