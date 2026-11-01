import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createExamStore } from "@/foundation/session/examStore";
import type { components } from "@/foundation/platform-client";

type Dashboard = components["schemas"]["Dashboard"];

const dash = (code: string) => ({ exam_codes: [code], current_exam_code: code, current_exam: null }) as unknown as Dashboard;

/** A fake api whose requests are settled by hand, and a clock moved by hand. */
function setup() {
  type Call = { userId: string; ok: (d: Dashboard) => void; fail: (e: Error) => void };
  const sent: Call[] = [];
  const calls = sent;
  /** The nth request sent, to settle by hand. */
  const call = (n: number): Call => {
    const found = sent[n];
    if (!found) throw new Error(`request ${n} was never sent`);
    return found;
  };
  let time = 1_000;
  const store = createExamStore(
    (userId) => new Promise<Dashboard>((ok, fail) => sent.push({ userId, ok, fail })),
    { now: () => time },
  );
  const tick = () => new Promise((r) => setTimeout(r, 0));
  return { store, calls, call, advance: (ms: number) => (time += ms), tick };
}

/** Two "hook instances": each subscribes and records what it last read. */
function mount(store: ReturnType<typeof setup>["store"], n = 2) {
  const seen = Array.from({ length: n }, () => store.getSnapshot());
  const unsubs = seen.map((_, i) => store.subscribe(() => (seen[i] = store.getSnapshot())));
  return { seen, unsubs };
}

describe("exam store", () => {
  it("sends one request for many instances starting together, and all see one answer", async () => {
    const { store, calls, call, tick } = setup();
    const { seen } = mount(store, 3);
    for (let i = 0; i < 3; i++) store.start("u1");
    assert.equal(calls.length, 1);
    assert.ok(seen.every((s) => s.loading && s.userId === "u1"));
    call(0).ok(dash("MRCP"));
    await tick();
    assert.ok(seen.every((s) => !s.loading && s.held.serverCurrent === "MRCP" && s.error === null));
    assert.equal(seen[0], seen[2]);
  });

  it("reuses a fresh answer for 10 seconds and asks again after", async () => {
    const { store, calls, call, advance, tick } = setup();
    mount(store, 1);
    store.start("u1");
    call(0).ok(dash("A"));
    await tick();
    advance(9_999);
    store.start("u1");
    assert.equal(calls.length, 1);
    assert.equal(store.getSnapshot().loading, false);
    advance(1);
    store.start("u1");
    assert.equal(calls.length, 2);
    // refreshing a known answer in the background does not flash a loading state
    assert.equal(store.getSnapshot().loading, false);
    assert.equal(store.getSnapshot().held.serverCurrent, "A");
  });

  it("reload sends a real request inside the sharing window and refreshes every instance", async () => {
    const { store, calls, call, tick } = setup();
    const { seen } = mount(store);
    store.start("u1");
    call(0).fail(new Error("boom"));
    await tick();
    assert.ok(seen.every((s) => s.error?.message === "boom" && !s.loading));
    store.reload(); // pressed on one instance only
    assert.equal(calls.length, 2);
    assert.ok(seen.every((s) => s.loading));
    call(1).ok(dash("B"));
    await tick();
    assert.ok(seen.every((s) => s.error === null && !s.loading && s.held.serverCurrent === "B"));
  });

  it("reload is a real request even when the shared answer is fresh", async () => {
    const { store, calls, call, tick } = setup();
    mount(store, 1);
    store.start("u1");
    call(0).ok(dash("A"));
    await tick();
    store.reload();
    assert.equal(calls.length, 2);
    call(1).ok(dash("C"));
    await tick();
    assert.equal(store.getSnapshot().held.serverCurrent, "C");
  });

  it("keeps the last answer when a refresh fails, and a mount inside the window does not re-ask", async () => {
    const { store, calls, call, advance, tick } = setup();
    mount(store, 1);
    store.start("u1");
    call(0).ok(dash("A"));
    await tick();
    store.reload();
    call(1).fail(new Error("down"));
    await tick();
    assert.equal(store.getSnapshot().held.serverCurrent, "A");
    assert.equal(store.getSnapshot().error?.message, "down");
    store.start("u1");
    assert.equal(calls.length, 2);
    advance(10_000); // a later screen reads fresh
    store.start("u1");
    assert.equal(calls.length, 3);
  });

  it("after a failed FIRST load the snapshot is settled: error set, nothing known, not loading", async () => {
    const { store, call, tick } = setup();
    mount(store, 1);
    store.start("u1");
    call(0).fail(new Error("502"));
    await tick();
    const { userId, held, error, loading } = store.getSnapshot();
    assert.deepEqual([userId, held.serverCurrent, held.codes, error?.message, loading], ["u1", null, [], "502", false]);
  });

  it("does not loop when a gate unmounts its screen while loading and remounts it when settled", async () => {
    // Capability renders null while loading, so the screen's own hook instance leaves and comes back.
    const { store, calls, call, tick } = setup();
    store.subscribe(() => gate()); // the nav footer / the gate itself, always mounted
    let screen: (() => void) | null = null;
    const mountScreen = () => {
      screen = store.subscribe(() => undefined);
      store.start("u1"); // the hook's effect
    };
    const gate = () => {
      const loading = store.getSnapshot().loading;
      if (loading && screen) {
        screen();
        screen = null;
      } else if (!loading && !screen) mountScreen();
    };
    mountScreen();
    for (let i = 0; i < 5; i++) {
      call(i).fail(new Error("502")); // would throw "never sent" the moment the loop stopped
      await tick();
      if (calls.length === i + 1) break;
    }
    assert.equal(calls.length, 1);
    assert.equal(store.getSnapshot().loading, false);
    assert.ok(screen, "the screen is mounted again, showing its explanation");
  });

  it("ignores a response superseded by a reload", async () => {
    const { store, call, tick } = setup();
    mount(store, 1);
    store.start("u1");
    store.reload();
    call(0).ok(dash("OLD"));
    await tick();
    assert.equal(store.getSnapshot().held.serverCurrent, null);
    assert.equal(store.getSnapshot().loading, true);
    call(1).ok(dash("NEW"));
    await tick();
    assert.equal(store.getSnapshot().held.serverCurrent, "NEW");
  });

  it("drops state at sign-out and ignores the response still in flight", async () => {
    const { store, calls, call, tick } = setup();
    mount(store, 1);
    store.start("u1");
    store.clear();
    call(0).ok(dash("U1"));
    await tick();
    assert.equal(store.getSnapshot().userId, null);
    assert.equal(store.getSnapshot().held.serverCurrent, null);
    store.reload(); // nobody is signed in: nothing to ask
    assert.equal(calls.length, 1);
  });

  it("never shows one person's exams to the next, and ignores the first person's late answer", async () => {
    const { store, calls, call, tick } = setup();
    mount(store, 1);
    store.start("u1");
    call(0).ok(dash("U1"));
    await tick();
    store.start("u2");
    assert.equal(calls.length, 2);
    assert.equal(store.getSnapshot().userId, "u2");
    assert.equal(store.getSnapshot().held.serverCurrent, null);
    assert.equal(store.getSnapshot().loading, true);
    store.start("u3"); // u2's request is still in flight when the person changes again
    call(1).ok(dash("U2"));
    await tick();
    assert.equal(store.getSnapshot().userId, "u3");
    assert.equal(store.getSnapshot().held.serverCurrent, null);
    call(2).ok(dash("U3"));
    await tick();
    assert.equal(store.getSnapshot().held.serverCurrent, "U3");
  });

  it("drops state when the last instance unmounts, but not across a route change", async () => {
    const { store, call, tick } = setup();
    const first = mount(store, 1);
    store.start("u1");
    call(0).ok(dash("A"));
    await tick();
    first.unsubs[0]?.();
    const second = mount(store, 1); // the next screen subscribes in the same commit
    await tick();
    assert.equal(store.getSnapshot().held.serverCurrent, "A");
    second.unsubs[0]?.();
    await tick();
    assert.equal(store.getSnapshot().userId, null);
    assert.equal(store.getSnapshot().held.serverCurrent, null);
  });

  it("hands useSyncExternalStore a stable snapshot until something changes", async () => {
    const { store, tick, call } = setup();
    mount(store, 1);
    const a = store.getSnapshot();
    assert.equal(store.getSnapshot(), a);
    store.start("u1");
    const b = store.getSnapshot();
    assert.notEqual(a, b);
    assert.equal(store.getSnapshot(), b);
    call(0).ok(dash("A"));
    await tick();
    assert.notEqual(store.getSnapshot(), b);
  });
});
