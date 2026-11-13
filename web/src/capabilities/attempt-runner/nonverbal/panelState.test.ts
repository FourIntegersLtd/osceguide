import assert from "node:assert/strict";
import { test } from "node:test";
import { cueLabel, feedRowTime, panelKind } from "./panelState";

const base = { supported: true, consented: true, off: false, isLive: true, status: "running" as const };
const lingo = { heading: "H", attention_label: "Attention", listening_label: "Listening", rapport_label: "Rapport" };

test("an unsupported attempt shows no panel", () => {
  assert.equal(panelKind({ ...base, supported: false }), "hidden");
});

test("not consented, or switched off, invites the candidate", () => {
  assert.equal(panelKind({ ...base, consented: false }), "invite");
  assert.equal(panelKind({ ...base, off: true }), "invite");
});

test("a refused or failed camera is reported even while live", () => {
  assert.equal(panelKind({ ...base, status: "denied" }), "denied");
  assert.equal(panelKind({ ...base, status: "unavailable" }), "unavailable");
});

test("consented and not live is ready; live is live, including while the camera starts", () => {
  assert.equal(panelKind({ ...base, isLive: false, status: "idle" }), "ready");
  assert.equal(panelKind({ ...base, status: "starting" }), "live");
  assert.equal(panelKind({ ...base, status: "running" }), "live");
});

test("each cue sits under the exam's own label", () => {
  assert.equal(cueLabel("attention", lingo), "Attention");
  assert.equal(cueLabel("nod", lingo), "Listening");
  assert.equal(cueLabel("smile", lingo), "Rapport");
});

test("a feed row shows minutes and seconds into the consultation", () => {
  assert.equal(feedRowTime(1_000_000 + 125_000, 1_000_000), "2:05");
  assert.equal(feedRowTime(500, 1_000), "0:00");
});
