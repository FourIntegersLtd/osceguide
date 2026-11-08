import assert from "node:assert/strict";
import test from "node:test";
import { initials, roleOf, tileName, tileStatus, turnLine, type RoomPerson } from "@/domains/assess/room/tileState";

const person = (over: Partial<RoomPerson>): RoomPerson => ({ role: "trainee", name: "Amara Okafor", isSelf: false, micAllowed: false, ...over });

test("reads the role from the LiveKit identity", () => {
  assert.equal(roleOf("agent-AJ_x"), "patient");
  assert.equal(roleOf("observer-123"), "supervisor");
  assert.equal(roleOf("5b9f"), "trainee");
});

test("names the viewer You and the patient Patient", () => {
  assert.equal(tileName({ role: "trainee", name: "Amara Okafor", isSelf: true }), "You");
  assert.equal(tileName({ role: "patient", name: "agent", isSelf: false }), "Patient");
  assert.equal(tileName({ role: "trainee", name: "  ", isSelf: false }), "Trainee");
  assert.equal(tileName({ role: "supervisor", name: "Dr Hale", isSelf: false }), "Dr Hale");
  assert.equal(tileName({ role: "supervisor", name: "observer-5b9f2c1e-1b0a-4fe3-9a11-000000000000", isSelf: false }), "Supervisor");
  assert.equal(tileName({ role: "trainee", name: "40984fe2-ff32-4d37-8949-2d376b3ad716", isSelf: false }), "Trainee");
});

test("shows muted for a person who may not speak, never for the patient", () => {
  assert.equal(tileStatus({ role: "trainee", micAllowed: false, speaking: false }), "muted");
  assert.equal(tileStatus({ role: "trainee", micAllowed: true, speaking: false }), "idle");
  assert.equal(tileStatus({ role: "patient", micAllowed: false, speaking: false }), "idle");
  assert.equal(tileStatus({ role: "trainee", micAllowed: true, speaking: true }), "speaking");
});

test("makes initials from the first two words", () => {
  assert.equal(initials("Amara Okafor Jr"), "AO");
  assert.equal(initials(""), "");
});

test("says whose turn it is, and when the floor is open", () => {
  const supervisor = person({ role: "supervisor", name: "Dr Hale", micAllowed: true });
  assert.equal(turnLine([supervisor, person({ micAllowed: true }), person({ name: "Ben Ade" })]).line, "Amara Okafor's turn.");
  assert.equal(turnLine([supervisor, person({ isSelf: true, micAllowed: true }), person({})]).line, "It's your turn.");
  const open = turnLine([supervisor, person({ micAllowed: true }), person({ name: "Ben Ade", micAllowed: true })]);
  assert.deepEqual(open, { line: "The floor is open. Everyone can speak.", floorOpen: true });
  assert.equal(turnLine([supervisor, person({})]).line, "Waiting for the next turn.");
});

test("is a turn, not an open floor, when one trainee is alone", () => {
  assert.deepEqual(turnLine([person({ micAllowed: true })]), { line: "Amara Okafor's turn.", floorOpen: false });
});
