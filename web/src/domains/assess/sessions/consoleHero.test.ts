import assert from "node:assert/strict";
import test from "node:test";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { examNowLine, heroSummary } from "@/domains/assess/sessions/consoleHero";
import { parseRail, toggleRail } from "@/domains/assess/sessions/railState";

const slot = (id: string, index: number, status: string, title = `S${index + 1}`) =>
  ({
    id,
    slot_index: index,
    status,
    exam_completed_at: null,
    trainee: { name: "Dr Sam", email: null },
    station: { title },
  }) as unknown as ConsoleSlot;

const frame = (circuit: Record<string, unknown>, slots: ConsoleSlot[]) =>
  ({ circuit: { started_at: null, ended_at: null, paused: false, phase: null, active_slot_id: null, ...circuit }, slots }) as unknown as CircuitConsole;

test("before it starts the hero says it is ready and what starting does", () => {
  const h = heroSummary(frame({}, [slot("a", 0, "scheduled")]));
  assert.equal(h.title, "Ready to start");
  assert.match(h.detail, /reading time for the first station/i);
});

test("a running station names the part, the station and the person", () => {
  const h = heroSummary(frame({ started_at: "t", phase: "reading", active_slot_id: "b" }, [slot("a", 0, "completed"), slot("b", 1, "reading", "Chest pain")]));
  assert.equal(h.title, "Reading time");
  assert.equal(h.detail, "Station 2 of 2 · Chest pain · Dr Sam");
});

test("paused outranks the phase", () => {
  assert.equal(heroSummary(frame({ started_at: "t", paused: true, phase: "simulation", active_slot_id: "a" }, [slot("a", 0, "in_consultation")])).title, "Paused");
});

test("an ended circuit counts what was sat", () => {
  const h = heroSummary(frame({ started_at: "t", ended_at: "u" }, [slot("a", 0, "completed"), slot("b", 1, "skipped")]));
  assert.deepEqual([h.title, h.detail], ["Circuit ended", "1 of 2 stations done · 0 marked"]);
});

test("rail state survives junk and toggles one section", () => {
  assert.deepEqual(parseRail("not json"), {});
  assert.deepEqual(parseRail(null), {});
  assert.deepEqual(parseRail('{"room":true,"x":1}'), { room: true });
  assert.deepEqual(toggleRail({ room: true }, "log"), { room: true, log: true });
  assert.deepEqual(toggleRail({ room: true }, "room"), { room: false });
});

import { nowLine, primaryTurnAction, turnsOf } from "@/domains/assess/sessions/turns";

const named = (id: string, index: number, status: string, name: string) =>
  ({ ...slot(id, index, status, `Station ${index + 1}`), trainee: { name, email: null } }) as unknown as ConsoleSlot;

test("turns: done, now, up next, waiting, and the primary names the next person", () => {
  const d = frame({ started_at: "t", active_slot_id: "b" }, [
    named("a", 0, "completed", "Amara"),
    named("b", 1, "in_consultation", "Tom"),
    named("c", 2, "scheduled", "Ife"),
    named("d", 3, "scheduled", "Joy"),
  ]);
  assert.deepEqual(turnsOf(d).rows.map((r) => r.state), ["done", "now", "next", "waiting"]);
  assert.equal(nowLine(d), "Now: Tom · Station 2");
  assert.deepEqual(primaryTurnAction(d), { kind: "advance", label: "Bring in Ife" });
});

test("turns: in reading time the primary starts the current turn, not the next person's", () => {
  const d = frame({ started_at: "t", active_slot_id: "b", phase: "reading" }, [
    named("a", 0, "completed", "Amara"),
    named("b", 1, "in_consultation", "Tom"),
    named("c", 2, "scheduled", "Ife"),
  ]);
  assert.deepEqual(primaryTurnAction(d), { kind: "advance", label: "Start Tom's turn" });
});

test("turns: after the last trainee the primary is End circuit", () => {
  const d = frame({ started_at: "t", active_slot_id: "b" }, [
    named("a", 0, "completed", "Amara"),
    named("b", 1, "in_consultation", "Tom"),
  ]);
  assert.deepEqual(primaryTurnAction(d), { kind: "end", label: "End circuit" });
});

test("exam: the hero names who is on and which station, and says so before anyone is on", () => {
  const d = frame({ started_at: "t", phase: "simulation", active_slot_id: "b" }, [slot("a", 0, "completed"), slot("b", 1, "in_consultation", "Chest pain"), slot("c", 2, "scheduled")]);
  assert.equal(examNowLine(d), "Now: Dr Sam · Station 2 of 3");
  assert.equal(examNowLine(frame({ started_at: "t", phase: "break" }, [slot("a", 0, "completed")])), "Between stations");
});
