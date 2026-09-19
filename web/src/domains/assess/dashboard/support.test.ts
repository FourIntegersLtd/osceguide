import assert from "node:assert/strict";
import test from "node:test";
import type { LiveCircuit, OrgDashboard, OrgSetup } from "@/domains/assess/dashboard/api";
import {
  boardOrder,
  candidatesLabel,
  circuitStatus,
  dashboardLead,
  nextStep,
  recordingMissing,
  setupProgress,
} from "@/domains/assess/dashboard/support";

function setup(over: Partial<OrgSetup> = {}): OrgSetup {
  return {
    trainees_added: false,
    stations_authored: false,
    team_invited: false,
    feedback_template_published: false,
    ready_to_run: false,
    ...over,
  };
}

function circuit(over: Partial<LiveCircuit> & { circuit_id: string }): LiveCircuit {
  return {
    circuit_name: `Circuit ${over.circuit_id}`,
    sitting_id: "s1",
    sitting_name: "June sitting",
    mode: "exam",
    room_name: "room-1",
    supervisor: null,
    candidates: [],
    current_station: null,
    phase: "simulation",
    phase_started_at: null,
    phase_ends_at: null,
    paused: false,
    auto_advance: true,
    elapsed_seconds: 0,
    remaining_seconds: 600,
    stations_total: 5,
    stations_completed: 1,
    attempt_id: "a1",
    attempt_status: "running",
    alerts: [],
    ...over,
  } as LiveCircuit;
}

function dashboard(over: Partial<OrgDashboard> = {}): OrgDashboard {
  return {
    org_id: "o1",
    slug: "st-marys",
    name: "St Mary's",
    counts: {
      trainees: 0,
      stations: 0,
      staff: 0,
      published_feedback_templates: 0,
      sittings: 0,
    },
    setup: setup(),
    recent_sittings: [],
    ...over,
  } as OrgDashboard;
}

test("the next step is the first one not done, in order", () => {
  assert.equal(nextStep(setup())?.key, "team");
  assert.equal(nextStep(setup({ team_invited: true }))?.key, "trainees");
  assert.equal(
    nextStep(
      setup({
        team_invited: true,
        trainees_added: true,
        stations_authored: true,
        feedback_template_published: true,
      }),
    ),
    null,
  );
});

test("progress counts what is done, not what the browser could fetch", () => {
  assert.deepEqual(setupProgress(setup({ team_invited: true, trainees_added: true })), {
    done: 2,
    total: 4,
    percent: 50,
  });
});

test("the lead says how much is left, then what to do next", () => {
  assert.match(dashboardLead(dashboard()), /4 steps left/);
  assert.match(
    dashboardLead(dashboard({ setup: setup({ ready_to_run: true }) })),
    /Schedule a sitting/,
  );
});

test("a consultation with no attempt behind it is a station nobody is recording", () => {
  assert.equal(recordingMissing(circuit({ circuit_id: "a" })), false);
  assert.equal(recordingMissing(circuit({ circuit_id: "a", attempt_id: null })), true);
  assert.equal(
    recordingMissing(circuit({ circuit_id: "a", attempt_status: "failed" })),
    true,
  );
  // Reading time has no recording yet and is not a problem.
  assert.equal(
    recordingMissing(circuit({ circuit_id: "a", phase: "reading", attempt_id: null })),
    false,
  );
});

test("the board puts trouble first, then whoever runs out of time soonest", () => {
  const calm = circuit({ circuit_id: "calm", remaining_seconds: 30 });
  const alerting = circuit({ circuit_id: "alerting", alerts: ["clock_overdue"], remaining_seconds: 900 });
  const soon = circuit({ circuit_id: "soon", remaining_seconds: 60 });
  assert.deepEqual(
    boardOrder([calm, alerting, soon]).map((each) => each.circuit_id),
    ["alerting", "calm", "soon"],
  );
});

test("a paused circuit says so rather than naming its phase", () => {
  assert.equal(circuitStatus(circuit({ circuit_id: "a", paused: true })), "Paused");
  assert.equal(circuitStatus(circuit({ circuit_id: "a", phase: "break" })), "Between stations");
  assert.equal(circuitStatus(circuit({ circuit_id: "a", phase: "reading" })), "Reading time");
});

test("a training circuit names the first people and counts the rest", () => {
  const people = (n: number) =>
    Array.from({ length: n }, (_, i) => ({ user_id: `u${i}`, name: `Person ${i}`, email: null }));
  assert.equal(candidatesLabel(circuit({ circuit_id: "a" })), "Nobody on this circuit");
  assert.equal(candidatesLabel(circuit({ circuit_id: "a", candidates: people(2) })), "Person 0 and Person 1");
  assert.equal(
    candidatesLabel(circuit({ circuit_id: "a", candidates: people(5) })),
    "Person 0, Person 1 and 3 more",
  );
});
