/**
 * Seeds the Trainee, TraineeSitting, TraineeResult, TraineeReview and SelfPractice boards
 * (docs/institution-overhaul/boards/Trainee*.dc.html, SelfPractice.dc.html). One organisation, four people with accounts:
 *  - Amara Okoye: March mock (station open), Year 3 practice round (training), Year 4 mock (finished, released, reviews).
 *  - Ben Hart: Winter mock (not started, "Before it opens") and Year 4 mock (finished, decision still a draft: "Not released").
 *  - Chloe Imran: on no sitting ("You are not booked on anything yet").
 * Sittings, circuits and decisions go through api routes; a finished circuit and its reviews are written with `psql`
 * (db.ts, local database only), as seed-results does.
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { call, orgPath } from "./api";
import { psql, q } from "./db";
import { STATION_CONTENT } from "./seed-exams";
import { decide, DOMAINS, finish } from "./seed-results";
import {
  seedSitting,
  seedSittingsOrg,
  type SittingsOrg,
} from "./seed-sittings";

export interface TraineeOrg extends SittingsOrg {
  sittings: { march: string; year3: string; year4: string; winter: string };
  /** Station slots of the Year 4 mock, by person index, in station order. */
  year4Slots: Record<number, string[]>;
  circuitIds: { march: string };
}

const NAMES = ["Amara Okoye", "Ben Hart", "Chloe Imran", "Dev Shah"];

function slotsOf(
  org: SittingsOrg,
  sittingId: string,
  person: number,
): string[] {
  const rows = psql(
    `SELECT sl.id FROM slots sl JOIN circuits c ON c.id = sl.circuit_id WHERE c.sitting_id = '${sittingId}' AND sl.trainee_id = '${org.people[person]?.userId}' ORDER BY sl.slot_index;`,
  );
  return rows.split("\n").filter(Boolean);
}

export async function seedTraineeOrg(): Promise<TraineeOrg> {
  const org = await seedSittingsOrg({
    adminName: "Ms Clarke",
    trainees: NAMES.length,
    names: NAMES,
    supervisors: ["Dr Patel"],
    domains: DOMAINS,
  });
  // Newest first on SelfPractice (sorted by title in the app): three published stations of the organisation's own.
  for (const title of [
    "Chest pain history",
    "Breaking bad news",
    "Headache history",
  ]) {
    const made = await call<{ id: string }>(
      org.token,
      orgPath(org.slug, "/stations"),
      {
        method: "POST",
        body: {
          title,
          exam_code: "finals",
          content: { title, ...STATION_CONTENT },
        },
      },
    );
    await call(
      org.token,
      orgPath(org.slug, `/stations/${made.id}/versions/1/publish`),
      { method: "POST" },
    );
  }
  const day = (offset: number) => {
    const d = new Date();
    d.setDate(d.getDate() + offset);
    d.setHours(9, 0, 0, 0);
    return d;
  };
  const year4 = await seedSitting(org, {
    name: "Year 4 mock",
    mode: "exam",
    exam: "year4",
    scheduledFor: day(-9),
    circuits: [0, 1].map((i) => ({
      name: `Circuit ${i + 1}`,
      people: [i],
      supervisor: "Dr Patel",
      stations: 3,
    })),
  });
  const year3 = await seedSitting(org, {
    name: "Year 3 practice round",
    mode: "training",
    exam: "year3",
    scheduledFor: day(7),
    circuits: [
      { name: "Circuit 1", people: [0, 3], supervisor: null, stations: 2 },
    ],
  });
  const winter = await seedSitting(org, {
    name: "Winter mock",
    mode: "exam",
    exam: "finals",
    scheduledFor: day(10),
    circuits: [
      { name: "Circuit 1", people: [1], supervisor: "Dr Patel", stations: 6 },
    ],
  });
  const march = await seedSitting(org, {
    name: "March mock",
    mode: "exam",
    exam: "finals",
    scheduledFor: day(0),
    start: true,
    readingMinutes: 600,
    circuits: [
      { name: "Circuit 1", people: [0], supervisor: "Dr Patel", stations: 6 },
    ],
  });
  finish(org, year4, [0, 1], "true");
  await decide(org, year4, 0, "pass", "released");
  await decide(org, year4, 1, "pass", "draft");
  psql(`UPDATE sittings SET status = 'completed' WHERE id = '${year4}';`);
  const year4Slots = { 0: slotsOf(org, year4, 0), 1: slotsOf(org, year4, 1) };

  // Completed reviews of every station but Amara's third (the board's "Not marked yet").
  const firstSlot = year4Slots[0][0];
  if (!firstSlot) throw new Error("no Year 4 slot");
  const { form } = await call<{ form: { fields: { path: string }[] } | null }>(
    org.token,
    orgPath(org.slug, `/slots/${firstSlot}/reviews`),
  );
  const fields = form?.fields ?? [];
  const values = JSON.stringify(
    Object.fromEntries(fields.map((f, i) => [f.path, i === 1 ? "A" : "G"])),
  );
  for (const slot of [...year4Slots[0].slice(0, 2), ...year4Slots[1]]) {
    psql(`INSERT INTO slot_reviews (id, slot_id, org_id, submitted_by, status, field_values, notes, completed_at)
      SELECT gen_random_uuid(), ${q(slot)}, sl.org_id, u.id, 'completed', ${q(values)}::jsonb, 'Clear structure and a safe plan. Ask about red flags earlier.', now() - interval '2 days'
      FROM slots sl, users u WHERE sl.id = ${q(slot)} AND u.email = ${q(org.account.email)};`);
  }
  // An exam slot's review reaches the candidate once the GP lead has completed theirs (Amara's third station never is).
  for (const slot of year4Slots[0].slice(0, 2)) {
    psql(`INSERT INTO gp_lead_reviews (id, slot_id, org_id, status, overall_rag, field_values, notes, reviewed_by, completed_at)
      SELECT gen_random_uuid(), ${q(slot)}, sl.org_id, 'completed', 'G', ${q(values)}::jsonb, 'Clear structure and a safe plan. Ask about red flags earlier.', u.id, now() - interval '2 days'
      FROM slots sl, users u WHERE sl.id = ${q(slot)} AND u.email = ${q(org.account.email)};`);
  }
  const circuit = psql(
    `SELECT c.id FROM circuits c WHERE c.sitting_id = '${march}' LIMIT 1;`,
  ).trim();
  return {
    ...org,
    sittings: { march, year3, year4, winter },
    year4Slots,
    circuitIds: { march: circuit },
  };
}

const CACHE = join(process.env.TMPDIR ?? tmpdir(), "board-trainee-org.json");

/**
 * The five Trainee board specs share one organisation: seeded once per day and re-read from a cache file after
 * (delete the file to reseed). Only the people's accounts and ids are used after seeding, never the admin's token.
 */
export async function traineeOrg(): Promise<TraineeOrg> {
  const today = new Date().toDateString();
  if (existsSync(CACHE)) {
    const saved = JSON.parse(readFileSync(CACHE, "utf8")) as {
      day: string;
      org: TraineeOrg;
    };
    if (saved.day === today) return saved.org;
  }
  const org = await seedTraineeOrg();
  writeFileSync(CACHE, JSON.stringify({ day: today, org }));
  return org;
}

/** The sign-in of the n-th person (0 Amara, 1 Ben, 2 Chloe). */
export const personAccount = (org: TraineeOrg, index: number) => ({
  email: org.people[index]?.email ?? "",
  password: org.account.password,
});
