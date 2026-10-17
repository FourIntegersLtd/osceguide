import assert from "node:assert/strict";
import { test } from "node:test";
import { lastWorkspace, rememberWorkspace } from "@/foundation/routing/lastWorkspace";

test("one account's last workspace is not the next account's", () => {
  const store = new Map<string, string>();
  (globalThis as unknown as Record<string, unknown>).window = {
    localStorage: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => void store.set(key, value),
    },
  };
  rememberWorkspace("learner-id", "me");
  assert.equal(lastWorkspace("learner-id"), "me");
  // An institution admin signing in next on the same browser was sent to `/app/me`.
  assert.equal(lastWorkspace("admin-id"), null);
});
