/**
 * Seeds the sample state of the Results, Sitting results and Slot review boards
 * (docs/institution-overhaul/boards/{Results,SittingResults,SlotReview}.dc.html): the March mock with eight
 * candidates and six stations each, Year 4 mock decided and released, a Year 3 training sitting.
 * Sittings, circuits, the roster and every decision go through existing api routes. The one thing the api
 * cannot produce locally is a finished, marked circuit (no LiveKit, no marking engine), so the rows a finished
 * circuit and its marking leave behind are written with `psql` from `db.ts`, local database only.
 */
import { call } from "./api";
import { psql } from "./db";
import { seedSitting, seedSittingsOrg, type SittingsOrg } from "./seed-sittings";

export const DOMAINS = ["History taking", "Communication", "Clinical reasoning"];
const NAMES = ["Amara Okoye", "Ben Hart", "Chloe Imran", "Dev Shah", "Esme Lowe", "Femi Adeyemi", "Grace Bell", "Hugo Stone"];

export interface SlotRow {
  slotId: string;
  attemptId: string | null;
  candidate: number;
  index: number;
}

export interface ResultsOrg extends SittingsOrg {
  sittings: { march: string; year4: string; year3: string };
  /** March mock slots, candidate by candidate, in station order. */
  marchSlots: SlotRow[];
}

function at(day: number, month: number): Date {
  return new Date(new Date().getFullYear(), month - 1, day, 9, 0);
}

/**
 * Finishes a sitting's circuits: every slot completed, an exam-slot attempt on each, and a marked result on
 * the attempts `marked` (a SQL boolean over `cand`, the person's index, and `idx`, the slot index) accepts.
 */
export function finish(org: SittingsOrg, sittingId: string, candidates: number[], marked: string): void {
  const users = candidates.map((i) => `'${org.people[i]?.userId}'`).join(",");
  const payload = DOMAINS.map((_, n) => `'domain_${n + 1}', jsonb_build_object('score', CASE WHEN cand = 1 THEN 'R' WHEN (cand + idx + ${n}) % 4 = 0 THEN 'A' ELSE 'G' END)`).join(", ");
  psql(`
DO $$
DECLARE
  s record; att uuid; ok boolean; cand int; idx int;
  people uuid[] := ARRAY[${users}]::uuid[];
  exam uuid := (select id from exams where code = 'sca' order by created_at limit 1);
BEGIN
  UPDATE circuits SET started_at = now() - interval '3 hours', ended_at = now() - interval '2 hours' WHERE sitting_id = '${sittingId}';
  FOR s IN SELECT sl.* FROM slots sl JOIN circuits c ON c.id = sl.circuit_id WHERE c.sitting_id = '${sittingId}' LOOP
    cand := array_position(people, s.trainee_id) - 1;
    idx := s.slot_index;
    ok := ${marked};
    UPDATE slots SET status = 'completed', started_at = now() - interval '3 hours', ended_at = now() - interval '2 hours', exam_completed_at = now() - interval '2 hours' WHERE id = s.id;
    att := gen_random_uuid();
    INSERT INTO attempts (id, kind, user_id, org_id, exam_id, station_version_id, slot_id, status, started_at, completed_at)
      VALUES (att, 'exam_slot', s.trainee_id, s.org_id, exam, s.station_version_id, s.id,
              CASE WHEN ok THEN 'evaluated' ELSE 'interaction_complete' END, now() - interval '3 hours', now() - interval '2 hours');
    IF ok THEN
      INSERT INTO assessment_results (id, attempt_id, framework_id, policy_version, model_used, payload, scored_at)
        VALUES (gen_random_uuid(), att, 'sca', 'e2e-fixture', 'fixture', jsonb_build_object(${payload}), now());
    END IF;
  END LOOP;
END $$;`);
}

export async function decide(org: SittingsOrg, sittingId: string, person: number, outcome: "pass" | "fail" | null, step: "draft" | "signed" | "released"): Promise<void> {
  const person_ = org.people[person];
  if (!person_) throw new Error(`no trainee ${person}`);
  const base = `/api/v1/orgs/${org.slug}/sittings/${sittingId}/candidates/${person_.traineeId}/decision`;
  const rationale = outcome === "pass" ? "Met the standard in every station." : outcome === "fail" && step !== "draft" ? "Did not show safe prioritisation in two stations." : null;
  await call(org.token, base, { method: "PUT", body: { assessment_outcome: outcome, rationale, expected_revision: 0 } });
  if (step === "draft") return;
  await call(org.token, `${base}/sign-off`, { method: "POST" });
  if (step === "released") await call(org.token, `${base}/release`, { method: "POST" });
}

export async function seedResultsOrg(): Promise<ResultsOrg> {
  const org = await seedSittingsOrg({ adminName: "Ms Clarke", trainees: 16, names: NAMES, supervisors: ["Dr Patel"], domains: DOMAINS });
  const all = (n: number) => Array.from({ length: n }, (_, i) => i);
  const today = new Date();
  today.setHours(9, 0, 0, 0);
  // Created in the board's reverse order so the newest-first lists read as the board's rows.
  const year3 = await seedSitting(org, {
    name: "Year 3 practice round", mode: "training", exam: "year3", scheduledFor: at(21, 10),
    circuits: [0, 1].map((c) => ({ name: `Circuit ${c + 1}`, people: all(8).map((i) => c * 8 + i), supervisor: null, stations: 8 })),
  });
  const year4 = await seedSitting(org, {
    name: "Year 4 mock", mode: "exam", exam: "year4", scheduledFor: at(28, 10),
    circuits: all(12).map((i) => ({ name: `Circuit ${i + 1}`, people: [i], supervisor: "Dr Patel", stations: 1 })),
  });
  const march = await seedSitting(org, {
    name: "March mock", mode: "exam", exam: "finals", scheduledFor: today,
    circuits: all(8).map((i) => ({ name: `Circuit ${i + 1}`, people: [i], supervisor: "Dr Patel", stations: 6 })),
  });
  // 40 of 48 marked: Chloe has two stations unmarked and Hugo none.
  finish(org, march, all(8), "NOT ((cand = 2 AND idx >= 4) OR cand = 7)");
  finish(org, year4, all(12), "true");
  // Amara, Dev and Esme signed off, Ben a draft fail with no rationale (the board's Ben has Fail chosen and nothing written); Year 4: three signed off, nine released.
  await decide(org, march, 0, "pass", "signed");
  await decide(org, march, 3, "pass", "signed");
  await decide(org, march, 4, "pass", "signed");
  await decide(org, march, 1, "fail", "draft");
  for (const i of all(12)) await decide(org, year4, i, "pass", i < 3 ? "signed" : "released");
  const rows = psql(`
SELECT sl.id, coalesce(a.id::text, ''), array_position(ARRAY[${all(8).map((i) => `'${org.people[i]?.userId}'`).join(",")}]::uuid[], sl.trainee_id) - 1, sl.slot_index
FROM slots sl JOIN circuits c ON c.id = sl.circuit_id LEFT JOIN attempts a ON a.slot_id = sl.id
WHERE c.sitting_id = '${march}' ORDER BY 3, 4;`);
  const marchSlots = rows.split("\n").map((line) => {
    const [slotId, attemptId, candidate, index] = line.split("|");
    return { slotId: slotId ?? "", attemptId: attemptId || null, candidate: Number(candidate), index: Number(index) };
  });
  return { ...org, sittings: { march, year4, year3 }, marchSlots };
}
