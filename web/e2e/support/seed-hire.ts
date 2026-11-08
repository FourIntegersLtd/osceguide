/**
 * Seeds the sample state of the HireHome board (docs/institution-overhaul/boards/HireHome.dc.html): an employer
 * organisation "Acme Health Trust" with 36 candidates, 4 assessors and 4 assessments, one of them running
 * (Band 6 nurse assessment day, assessor Dr Patel) and one finished with 4 candidates waiting on a hiring decision.
 * `{ training: true }` adds a fifth, a finished training rotation (HIRE-6), which the board specs do not expect.
 * Existing api routes only; the finished circuit's rows are written like the Results seed does (local database).
 */
import { call, orgPath } from "./api";
import { psql } from "./db";
import { STATION_CONTENT } from "./seed-exams";
import { addTrainees, fillers, haveSignedIn } from "./seed-people";
import { finish } from "./seed-results";
import { seedSitting, seedSittingsOrg, type SittingsOrg } from "./seed-sittings";

const NAMES = ["Amara Okoye", "Ben Hart", "Chloe Imran", "Dev Shah", "Esme Lowe", "Femi Adeyemi", "Grace Bell"];

export async function seedHireOrg(options: { training?: boolean } = {}): Promise<SittingsOrg> {
  const org = await seedSittingsOrg({
    adminName: "Ms Clarke",
    trainees: NAMES.length,
    names: NAMES,
    supervisors: ["Dr Patel", "Dr Quinn", "Dr Reid"],
    org: { type: "employer", name: "Acme Health Trust" },
  });
  // One published station of the organisation's own: without it the dashboard shows the setup assistant.
  const title = "Chest pain history";
  const station = await call<{ id: string }>(org.token, orgPath(org.slug, "/stations"), { method: "POST", body: { title, exam_code: "finals", content: { title, ...STATION_CONTENT } } });
  await call(org.token, orgPath(org.slug, `/stations/${station.id}/versions/1/publish`), { method: "POST" });
  const day = (offset: number) => {
    const d = new Date();
    d.setDate(d.getDate() + offset);
    d.setHours(9, 0, 0, 0);
    return d;
  };
  const single = (people: number[], supervisor: string, stations = 2) => people.map((p, i) => ({ name: `Circuit ${i + 1}`, people: [p], supervisor, stations }));
  // Newest first on the board's lists: create the oldest first.
  await seedSitting(org, { name: "Band 5 recruitment day", mode: "exam", exam: "finals", scheduledFor: day(-7), circuits: single([3, 4, 5, 6], "Dr Patel") });
  for (const [n, offset] of [[1, 7], [2, 14], [3, 21]] as const) {
    await seedSitting(org, { name: `Band 7 panel ${n}`, mode: "exam", exam: "year3", scheduledFor: day(offset), circuits: single([n], "Dr Quinn") });
  }
  if (options.training) {
    // A finished training rotation: the results page must say there are no hiring decisions (HIRE-6).
    const practice = await seedSitting(org, { name: "Band 5 training rotation", mode: "training", exam: "finals", scheduledFor: day(-3), circuits: single([6], "Dr Quinn", 1) });
    finish(org, practice, [6], "true");
    psql(`UPDATE sittings SET status = 'completed' WHERE id = '${practice}';`);
  }
  await seedSitting(org, {
    name: "Band 6 nurse assessment day", mode: "exam", exam: "year4", scheduledFor: day(0), start: true, readingMinutes: 60,
    circuits: single([0, 1, 2], "Dr Patel", 3),
  });
  // All three circuits of the running day are live (seedSitting starts the first).
  const running = psql(`SELECT c.id FROM circuits c JOIN sittings s ON s.id = c.sitting_id WHERE s.name = 'Band 6 nurse assessment day' AND c.started_at IS NULL AND s.org_id = (SELECT id FROM organizations WHERE slug = '${org.slug}');`);
  for (const id of running.split("\n").filter(Boolean)) await call(org.token, orgPath(org.slug, `/circuits/${id}/start`), { method: "POST" });
  const done = psql(`SELECT s.id FROM sittings s WHERE s.name = 'Band 5 recruitment day' AND s.org_id = (SELECT id FROM organizations WHERE slug = '${org.slug}');`).trim();
  finish(org, done, [3, 4, 5, 6], "true");
  psql(`UPDATE sittings SET status = 'completed' WHERE id = '${done}';`);
  await addTrainees(org, fillers(29));
  haveSignedIn([...org.people.map((p) => p.email), ...fillers(29).map((p) => p.email)]);
  return org;
}
