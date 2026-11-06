/**
 * Seeds the sample state of the Today, SupervisorHome and LiveBoard boards
 * (docs/institution-overhaul/boards/{Today,SupervisorHome,LiveBoard}.dc.html) on top of the Results organisation
 * (March mock marked, Year 4 mock decided): the sittings the boards list, the circuit running now (Circuit A,
 * Dr Patel, eight stations; a formal-exam circuit holds one candidate, the board's eight cannot be seeded), four trainees who have not joined, and Dr Patel's next circuit.
 * Existing api routes only; the finished circuits come from seed-results (local database).
 */
import { call, orgPath } from "./api";
import { STATION_CONTENT } from "./seed-exams";
import { psql, q } from "./db";
import { addTrainees } from "./seed-people";
import { seedResultsOrg, type ResultsOrg } from "./seed-results";
import { seedSitting } from "./seed-sittings";

export interface HomeOrg extends ResultsOrg {
  /** Dr Patel's sign-in, for the supervisor home. */
  supervisor: { email: string; password: string };
}

const at = (day: number, month: number, hour = 9) => new Date(new Date().getFullYear(), month - 1, day, hour, 0);

export async function seedHomeOrg(): Promise<HomeOrg> {
  const org = await seedResultsOrg();
  // One published station of the organisation's own: without it the dashboard shows the setup assistant.
  const title = "Chest pain history";
  const station = await call<{ id: string }>(org.token, orgPath(org.slug, "/stations"), { method: "POST", body: { title, exam_code: "finals", content: { title, ...STATION_CONTENT } } });
  await call(org.token, orgPath(org.slug, `/stations/${station.id}/versions/1/publish`), { method: "POST" });
  // The board greets "Dr Okafor".
  psql(`UPDATE users SET name = 'Dr Okafor' WHERE email = ${q(org.account.email)};`);
  // The running circuit's candidate line is as short as the board's "8 candidates" on a phone.
  psql(`UPDATE users SET name = 'Ana Yu' WHERE id = '${org.people[0]?.userId}';`);
  const all = (n: number) => Array.from({ length: n }, (_, i) => i);
  await addTrainees(org, [1, 2, 3, 4].map((n) => ({ first: "Pending", last: `Invitee${n}`, email: `pending-${n}-${org.slug}@example.com` })));
  // Newest first on the lists: the oldest is created first.
  await seedSitting(org, {
    name: "Final-year OSCE, summer finals", mode: "exam", exam: "finals", scheduledFor: at(26, 11),
    circuits: all(6).map((i) => ({ name: `Circuit ${i + 1}`, people: [8 + i], supervisor: i === 0 ? "Dr Patel" : null, stations: 4 })),
  });
  await seedSitting(org, {
    name: "Year 3 practice round", mode: "training", exam: "year3", scheduledFor: at(12, 11),
    circuits: [{ name: "Circuit B", people: all(8), supervisor: "Dr Patel", stations: 8 }],
  });
  await seedSitting(org, {
    name: "Final-year OSCE, March mock", mode: "exam", exam: "finals", scheduledFor: new Date(), start: true,
    circuits: [{ name: "Circuit A", people: [0], supervisor: "Dr Patel", stations: 8 }],
  });
  const supervisor = org.staffAccounts["Dr Patel"];
  if (!supervisor) throw new Error("no Dr Patel account");
  // Circuits that ended earlier, for the live board's history (written by the api when a circuit ends).
  const ended = (name: string, sitting: string, mode: string, at: string, from: string, count: number, done: number, status: string) =>
    `INSERT INTO circuit_run_history (id, org_id, circuit_name, sitting_name, mode, started_at, ended_at, candidate_count, stations_total, stations_completed, status)
     SELECT gen_random_uuid(), id, '${name}', '${sitting}', '${mode}', '${from}', '${at}', ${count}, 6, ${done}, '${status}' FROM organizations WHERE slug = ${q(org.slug)};`;
  psql(
    [
      ended("Circuit 2", "March mock", "exam", "2026-11-05 10:24", "2026-11-05 09:00", 1, 6, "completed"),
      ended("Circuit 5", "March mock", "exam", "2026-11-05 09:58", "2026-11-05 09:00", 1, 4, "ended_early"),
      ended("Morning circuit", "Year 3 practice round", "training", "2026-11-04 15:10", "2026-11-04 14:00", 6, 6, "completed"),
    ].join("\n"),
  );
  return { ...org, supervisor };
}
