import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { NextRequest } from "next/server";

import { POST } from "@/app/api/session/token/route";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

/** platform-api refuses every refresh: the chain was spent. */
function refreshRefused(): void {
  globalThis.fetch = async () => new Response(JSON.stringify({ code: "invalid_refresh_token" }), { status: 401 });
}

function ask(refreshToken: string, body: object = {}): NextRequest {
  return new NextRequest("http://localhost:3100/api/session/token", {
    method: "POST",
    headers: { cookie: `osce_rt=${refreshToken}; osce_session=1`, "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

function cleared(response: Response): boolean {
  return response.headers.getSetCookie().some((cookie) => cookie.startsWith("osce_rt=;"));
}

test("a refused refresh leaves the cookies alone and names the refused token", async () => {
  refreshRefused();
  const response = await POST(ask("spent-token"));
  const body = (await response.json()) as { access_token: null; refused: string };
  assert.equal(body.access_token, null);
  assert.equal(typeof body.refused, "string");
  assert.equal(cleared(response), false);
});

test("checking back with the cookie unchanged ends the session", async () => {
  refreshRefused();
  const { refused } = (await (await POST(ask("spent-token"))).json()) as { refused: string };
  const response = await POST(ask("spent-token", { refused }));
  assert.deepEqual(await response.json(), { access_token: null });
  assert.equal(cleared(response), true);
});

test("a pair another tab stored meanwhile survives the check-back", async () => {
  refreshRefused();
  const { refused } = (await (await POST(ask("spent-token"))).json()) as { refused: string };
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ access_token: "fresh-access", refresh_token: "next-token", expires_in: 900 }));
  const response = await POST(ask("token-from-the-other-tab", { refused }));
  assert.equal(((await response.json()) as { access_token: string }).access_token, "fresh-access");
  assert.equal(cleared(response), false);
});
