import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { listActiveTrainees, type Trainee } from "@/domains/assess/api";
import { NOT_YET_JOINED, latecomerChoices } from "@/domains/assess/sessions/latecomers";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function trainee(index: number, userId: string | null): Trainee {
  return { id: `t${index}`, email: `t${index}@example.com`, user_id: userId, access_revoked: false } as Trainee;
}

// S-9: the pickers read the first 100 of the roster and dropped anyone with no user_id.
test("the latecomer list reads every page and shows a trainee who has not joined, unpickable, with the reason", async () => {
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    assert.equal(url.searchParams.get("access_revoked"), "false");
    const page = Number(url.searchParams.get("cursor") ?? "0");
    const items = Array.from({ length: 100 }, (_, offset) => {
      const index = page * 100 + offset;
      return trainee(index, index === 150 ? null : `u${index}`);
    });
    return new Response(JSON.stringify({ items, next_cursor: page < 2 ? String(page + 1) : null }), { status: 200 });
  }) as typeof fetch;

  const roster = await listActiveTrainees("kings");
  assert.equal(roster.length, 300);

  const choices = latecomerChoices(roster, [{ trainee: { user_id: "u0" } }]);
  assert.equal(choices.length, 299);
  const last = choices.at(-1);
  assert.deepEqual([last?.trainee.id, last?.refusal], ["t150", NOT_YET_JOINED]);
  assert.equal(NOT_YET_JOINED, "Not yet joined: they can be added once they have signed in.");
  assert.equal(choices.filter((choice) => choice.refusal === null).length, 298);
});
