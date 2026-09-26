import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { GET } from "@/app/version/route";

describe("GET /version", () => {
  it("answers with the build's commit sha, read straight from Vercel's env var", async () => {
    process.env.VERCEL_GIT_COMMIT_SHA = "abc1234";
    const response = GET();
    assert.equal(response.status, 200);
    const body = (await response.json()) as { commit: string };
    assert.deepEqual(body, { commit: "abc1234" });
    delete process.env.VERCEL_GIT_COMMIT_SHA;
  });

  it("answers with an empty commit rather than throwing when the var is unset", async () => {
    delete process.env.VERCEL_GIT_COMMIT_SHA;
    const response = GET();
    const body = (await response.json()) as { commit: string };
    assert.deepEqual(body, { commit: "" });
  });
});
