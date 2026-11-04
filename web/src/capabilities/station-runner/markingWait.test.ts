import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { SLOW_AFTER_MS, markingWillNotArrive, watchMarking, type MarkingWaitTimers } from "@/capabilities/station-runner/markingWait";

/** A clock the test moves by hand, so ten minutes of waiting takes no time. */
function fakeClock() {
  let now = 0;
  let next = 1;
  const pending = new Map<number, { at: number; run: () => void }>();
  const timers: MarkingWaitTimers = {
    now: () => now,
    setTimeout: (run, ms) => {
      const id = next++;
      pending.set(id, { at: now + ms, run });
      return id;
    },
    clearTimeout: (handle) => {
      pending.delete(handle as number);
    },
  };
  /** Advance time, running every timer that falls due, and let the checks they start settle. */
  const advance = async (ms: number) => {
    const until = now + ms;
    for (;;) {
      const due = [...pending.entries()].filter(([, t]) => t.at <= until).sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      pending.delete(due[0]);
      now = due[1].at;
      due[1].run();
      await settle();
    }
    now = until;
  };
  return { timers, advance, pendingCount: () => pending.size };
}

const settle = () => new Promise<void>((resolve) => setImmediate(resolve));

describe("watchMarking", () => {
  it("reads once on start and then only on a wake-up: ten minutes of silence costs no reads", async () => {
    const clock = fakeClock();
    let checks = 0;
    const events: string[] = [];
    const wait = watchMarking({
      isMarked: async () => {
        checks += 1;
        return false;
      },
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });

    await settle();
    await clock.advance(10 * 60 * 1000);
    assert.equal(checks, 1);
    assert.deepEqual(events, ["slow"]);

    wait.wake();
    await settle();
    assert.equal(checks, 2);
    wait.wake();
    await settle();
    assert.equal(checks, 3);
  });

  it("goes slow after SLOW_AFTER_MS without reading anything", async () => {
    const clock = fakeClock();
    let checks = 0;
    const events: string[] = [];
    watchMarking({
      isMarked: async () => {
        checks += 1;
        return false;
      },
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });
    await settle();
    await clock.advance(SLOW_AFTER_MS - 1);
    assert.deepEqual(events, []);
    await clock.advance(1);
    assert.deepEqual(events, ["slow"]);
    assert.equal(checks, 1);
  });

  it("shows the feedback on the wake-up after the slow message, however late the result is stored", async () => {
    const clock = fakeClock();
    let stored = false;
    const events: string[] = [];
    const wait = watchMarking({
      isMarked: async () => stored,
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });

    await clock.advance(10 * 60 * 1000);
    stored = true;
    wait.wake();
    await settle();
    assert.deepEqual(events, ["slow", "ready"]);
    assert.equal(clock.pendingCount(), 0);
  });

  it("finds a result stored before the wait started, with no event at all", async () => {
    const clock = fakeClock();
    const events: string[] = [];
    watchMarking({
      isMarked: async () => true,
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });
    await settle();
    assert.deepEqual(events, ["ready"]);
    assert.equal(clock.pendingCount(), 0);
  });

  it("treats a failed read (a 502 during an API restart) as not yet; the next wake-up reads again", async () => {
    const clock = fakeClock();
    let calls = 0;
    const events: string[] = [];
    const wait = watchMarking({
      isMarked: async () => {
        calls += 1;
        if (calls <= 1) throw new Error("502 Bad Gateway");
        return true;
      },
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });

    await settle();
    assert.deepEqual(events, []);
    wait.wake();
    await settle();
    assert.deepEqual(events, ["ready"]);
    assert.equal(calls, 2);
  });

  it("does nothing more once stopped", async () => {
    const clock = fakeClock();
    let calls = 0;
    const wait = watchMarking({
      isMarked: async () => {
        calls += 1;
        return true;
      },
      onReady: () => assert.fail("closed modal must not navigate"),
      onSlow: () => assert.fail("closed modal must not turn slow"),
      timers: clock.timers,
    });
    wait.stop();
    wait.wake();
    await clock.advance(10 * 60 * 1000);
    assert.equal(calls <= 1, true);
    assert.equal(clock.pendingCount(), 0);
  });
});

describe("watchMarking on a failed attempt", () => {
  it("says so at the next check instead of waiting for ever, and stops", async () => {
    const clock = fakeClock();
    let failed = false;
    const events: string[] = [];
    const wait = watchMarking({
      isMarked: async () => false,
      failure: {
        check: async () => failed,
        onFailed: () => events.push("failed"),
      },
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });
    await settle();
    assert.deepEqual(events, []);
    failed = true;
    wait.wake();
    await settle();
    assert.deepEqual(events, ["failed"]);
    assert.equal(clock.pendingCount(), 0);
  });
});

describe("markingWillNotArrive", () => {
  it("is true for an attempt the scorer gave up on or that failed outright", () => {
    assert.equal(markingWillNotArrive({ status: "failed" }), true);
    assert.equal(markingWillNotArrive({ status: "interaction_complete", marking_failed: true }), true);
    assert.equal(markingWillNotArrive({ status: "interaction_complete" }), false);
  });
});
