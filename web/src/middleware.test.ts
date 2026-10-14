import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { NextRequest, type NextFetchEvent } from "next/server";
import { middleware } from "@/middleware";
import { SESSION_COOKIES } from "@/foundation/platform-client/sessionCookies";

const event = { waitUntil() {} } as unknown as NextFetchEvent;

function visit(url: string, signedIn: boolean) {
  const headers = signedIn ? { cookie: `${SESSION_COOKIES.refresh}=token` } : undefined;
  return middleware(new NextRequest(url, { headers }), event);
}

describe("the front door", () => {
  it("sends a signed-in visitor on / to /app with a 307", () => {
    const response = visit("https://osceguide.com/", true);
    assert.equal(response.status, 307);
    assert.equal(new URL(response.headers.get("location") ?? "").pathname, "/app");
  });

  it("serves the landing to a visitor with no session cookie", () => {
    const response = visit("https://osceguide.com/", false);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("location"), null);
  });

  it("leaves other public pages alone for a signed-in visitor", () => {
    assert.equal(visit("https://osceguide.com/pricing", true).headers.get("location"), null);
  });
});
