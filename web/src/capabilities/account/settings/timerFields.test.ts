import assert from "node:assert/strict";
import test from "node:test";
import { describeTimer, formatTimer, parseTimer } from "@/capabilities/account/settings/timerFields";

test("a timer field reads and writes minutes and seconds", () => {
  assert.equal(formatTimer(240), "04:00");
  assert.equal(formatTimer(875), "14:35");
  assert.equal(parseTimer("04:00"), 240);
  assert.equal(parseTimer("14"), 840);
  assert.equal(parseTimer(" 14:35 "), 875);
});

test("a timer that is empty, zero, malformed or over an hour is refused", () => {
  assert.equal(parseTimer(""), null);
  assert.equal(parseTimer("00:00"), null);
  assert.equal(parseTimer("4:75"), null);
  assert.equal(parseTimer("61:00"), null);
  assert.equal(parseTimer("four"), null);
});

test("the timers are described in words", () => {
  assert.equal(describeTimer(240), "4 min");
  assert.equal(describeTimer(270), "4 min 30 s");
});
