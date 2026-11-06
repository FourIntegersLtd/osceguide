/**
 * Seeds the sample state of the Console, Edit circuit and Circuit feedback boards
 * (docs/institution-overhaul/boards/{Console,EditCircuit,CircuitReview}.dc.html) on top of the Sittings seed:
 * Dr Patel (the signed-in administrator, also the circuits' supervisor), eight named people (example.com only), and
 *  - "March mock" (exam): Circuit 1 · Amara Okoye running on station 2 in consultation, Circuit 2 not started,
 *    Circuit 3 · Chloe Imran ended with six stations sat, four of them marked;
 *  - "Year 3 practice round" (training): one running circuit of three people.
 * Everything goes through existing api routes; the clock position (station 2 in consultation) and the slots' sat state
 * cannot be reached locally without a voice room, so they are set with the same SQL the other e2e fixtures use
 * (`psql` in ./db.ts). What the api still cannot be made to show is a named exception in the specs.
 */
import { call, orgPath } from "./api";
import { psql, seedMarkedSlotAttempt } from "./db";
import { ensureTitledStations, seedSittingsOrg, type SittingsOrg } from "./seed-sittings";

/** The board's station titles (Chest pain history, Breaking bad news, Abdominal examination); 4 to 6 are the same length. */
export const STATION_TITLES = ["Chest pain history", "Breaking bad news", "Abdominal examination", "Diabetic review", "Thyroid examination", "Consent for surgery"];

export const NAMES = ["Amara Okoye", "Ben Hart", "Chloe Imran", "Dev Shah", "Farah Ali", "Gil Moss", "Hana Lee", "Ivan Novak"];

export interface ConsoleWorld {
  org: SittingsOrg;
  sittingId: string;
  trainingSittingId: string;
  /** Exam circuit running on station 2. */
  live: string;
  /** Exam circuit not started. */
  fresh: string;
  /** Exam circuit that has ended (four of six stations marked). */
  ended: string;
  /** Training circuit running, three people. */
  training: string;
  /** Slot ids of the live exam circuit, in order. */
  liveSlots: string[];
}

interface Created {
  id: string;
}

async function makeSitting(org: SittingsOrg, name: string, mode: "exam" | "training", exam: "finals" | "year3"): Promise<string> {
  const today = new Date();
  today.setHours(9, 0, 0, 0);
  const made = await call<Created>(org.token, orgPath(org.slug, `/sittings`), {
    method: "POST",
    body: {
      name,
      mode,
      sitting_type: mode === "exam" ? "mock_exam" : "group_training",
      programme_id: org.exams[exam].programmeId,
      scheduled_for: today.toISOString(),
    },
  });
  return made.id;
}

async function makeCircuit(org: SittingsOrg, sittingId: string, name: string, people: number[], stations: number, supervisor: string | null): Promise<string> {
  const made = await call<Created>(org.token, orgPath(org.slug, `/sittings/${sittingId}/circuits`), {
    method: "POST",
    body: {
      name,
      station_version_ids: org.stationVersionIds.slice(0, stations),
      trainee_ids: people.map((i) => org.people[i]?.userId),
      supervisor_user_id: supervisor ? org.staff[supervisor] : undefined,
      timing: { reading_minutes: 2, simulation_minutes: 10 },
    },
  });
  return made.id;
}

const circuitPath = (org: SittingsOrg, id: string, tail: string) => orgPath(org.slug, `/circuits/${id}${tail}`);

async function slotIds(org: SittingsOrg, circuit: string): Promise<string[]> {
  const frame = await call<{ slots: { id: string; slot_index: number }[] }>(org.token, circuitPath(org, circuit, "/console"));
  return frame.slots.slice().sort((a, b) => a.slot_index - b.slot_index).map((slot) => slot.id);
}

/** Station `at` (0-based) of a started circuit is in consultation with an hour on the clock; the ones before it are sat. */
function moveTo(circuit: string, slots: string[], at: number): void {
  const earlier = slots.slice(0, at).map((id) => `'${id}'`).join(",") || "NULL";
  psql(`
UPDATE slots SET status = 'completed', ended_at = now() WHERE id IN (${earlier});
UPDATE slots SET status = 'in_consultation' WHERE id = '${slots[at]}';
UPDATE circuits SET active_slot_id = '${slots[at]}', phase = 'simulation', phase_started_at = now(),
  phase_ends_at = now() + interval '1 hour' WHERE id = '${circuit}';`);
}

export async function seedConsoleWorld(): Promise<ConsoleWorld> {
  const org = await seedSittingsOrg({ adminName: "Dr Patel", trainees: NAMES.length, names: NAMES, supervisors: ["Ms Clarke"] });
  org.stationVersionIds = await ensureTitledStations(STATION_TITLES);
  const start = (id: string) => call(org.token, circuitPath(org, id, "/start"), { method: "POST" });

  const sittingId = await makeSitting(org, "March mock", "exam", "finals");
  const live = await makeCircuit(org, sittingId, "Circuit 1 · Amara Okoye", [0], 3, "Dr Patel");
  const fresh = await makeCircuit(org, sittingId, "Circuit 2", [1], 6, "Dr Patel");
  const ended = await makeCircuit(org, sittingId, "Circuit 3 · Chloe Imran", [2], 6, "Dr Patel");

  await start(live);
  const liveSlots = await slotIds(org, live);
  moveTo(live, liveSlots, 1);
  for (const id of liveSlots.slice(0, 1)) seedMarkedSlotAttempt(id);

  await start(ended);
  await call(org.token, circuitPath(org, ended, "/end"), { method: "POST", body: {} });
  const endedSlots = await slotIds(org, ended);
  psql(`UPDATE slots SET status = 'completed' WHERE id IN (${endedSlots.map((id) => `'${id}'`).join(",")});`);
  for (const id of endedSlots.slice(0, 4)) seedMarkedSlotAttempt(id);

  const trainingSittingId = await makeSitting(org, "Year 3 practice round", "training", "year3");
  // The api builds a training circuit with one slot per trainee, each at a different station (domain.build_slots), and
  // walks the slots in order exactly as for an exam (domain_run.py: "rotate the group" and "walk one candidate" are the
  // same walk). So "slot 0 sat, slot 1 in consultation" is a state the api reaches; only the clock is set by hand.
  const training = await makeCircuit(org, trainingSittingId, "Circuit 1", [4, 5, 6], 3, "Dr Patel");
  await start(training);
  const trainingSlots = await slotIds(org, training);
  moveTo(training, trainingSlots, 1);
  // Three entries for "What was changed by hand" (the board lists nine; one of each action is not reachable without a voice room).
  await call(org.token, circuitPath(org, training, "/pause"), { method: "POST", body: { reason: "Fire alarm test" } });
  await call(org.token, circuitPath(org, training, "/resume"), { method: "POST", body: {} });
  await call(org.token, circuitPath(org, training, "/extend-clock"), { method: "POST", body: { seconds: 60, reason: "Fire alarm test" } });

  return { org, sittingId, trainingSittingId, live, fresh, ended, training, liveSlots };
}
