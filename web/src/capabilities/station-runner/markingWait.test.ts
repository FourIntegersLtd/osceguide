import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { SLOW_AFTER_MS, watchMarking, type MarkingWaitTimers } from "@/capabilities/station-runner/markingWait";

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
  it("shows the feedback when marking is stored after ten minutes, past the old give-up point", async () => {
    const clock = fakeClock();
    const storedAt = 10 * 60 * 1000;
    let checks = 0;
    const events: string[] = [];
    watchMarking({
      isMarked: async () => {
        checks += 1;
        return clock.timers.now() >= storedAt;
      },
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });

    await clock.advance(9 * 60 * 1000);
    assert.deepEqual(events, ["slow"]);
    assert.ok(checks > 10, `still checking after the old ten-try limit (made ${checks})`);

    // Stored at 10:00; found by the next check, at most the 30-second ceiling later.
    await clock.advance(90 * 1000);
    assert.deepEqual(events, ["slow", "ready"]);
    assert.equal(clock.pendingCount(), 0);
  });

  it("checks at once on a wake-up, so a missed or early event costs nothing", async () => {
    const clock = fakeClock();
    let stored = false;
    const events: string[] = [];
    const wait = watchMarking({
      isMarked: async () => stored,
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });

    await clock.advance(SLOW_AFTER_MS + 30_000);
    stored = true; // stored while the stream was down: no event reached this tab
    wait.wake(); // the stream reconnects and asks every panel to re-read
    await settle();
    assert.deepEqual(events, ["slow", "ready"]);
  });

  it("treats a failed read (a 502 during an API restart) as not yet, and keeps waiting", async () => {
    const clock = fakeClock();
    let calls = 0;
    const events: string[] = [];
    watchMarking({
      isMarked: async () => {
        calls += 1;
        if (calls <= 3) throw new Error("502 Bad Gateway");
        return true;
      },
      onReady: () => events.push("ready"),
      onSlow: () => events.push("slow"),
      timers: clock.timers,
    });

    await clock.advance(60 * 1000);
    assert.deepEqual(events, ["ready"]);
    assert.equal(calls, 4);
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
      onSlow: () => undefined,
      timers: clock.timers,
    });
    wait.stop();
    wait.wake();
    await clock.advance(10 * 60 * 1000);
    assert.equal(calls, 0);
  });
});
