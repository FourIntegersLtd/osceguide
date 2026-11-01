/**
 * The one database seam: a marked practice attempt. Marking is done by the
 * engine from a spoken transcript, which cannot exist here (no LiveKit), so
 * the row a finished marking leaves behind is written directly, the way
 * .claude/skills/verify/features/marked-slot-fixture.sql does. It only runs
 * after assertLocalApi(), against the docker postgres of the local api.
 */
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { assertLocalApi } from "./api";

/** The one marked result both fixtures carry: a Green rating with a quoted phrase. */
const GREEN_PAYLOAD = JSON.stringify({
  global_skills: { structures_consultation: { score: "G", supporting_phrase: "Shall we start with what brought you in?", explanation: "Clear opening." } },
});

const CONTAINER = process.env.E2E_PG_CONTAINER ?? "platform-api-postgres-1";

/** CI has Postgres as a service, not a named container: E2E_DATABASE_URL points psql at it. */
const DATABASE_URL = process.env.E2E_DATABASE_URL;

function psql(sql: string): string {
  assertLocalApi();
  const [command, args]: [string, string[]] = DATABASE_URL
    ? ["psql", [DATABASE_URL, "-At", "-v", "ON_ERROR_STOP=1"]]
    : ["docker", ["exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "osce_platform", "-At", "-v", "ON_ERROR_STOP=1"]];
  return execFileSync(command, args, {
    input: sql,
    encoding: "utf8",
  }).trim();
}

/** One evaluated SCA practice attempt, with a Green rating, for the user. Returns the attempt id. */
export function seedMarkedPracticeAttempt(email: string): string {
  const a = randomUUID();
  psql(`
DO $$
DECLARE
  u uuid := (select id from users where email = '${email.replace(/'/g, "''")}');
  exam uuid := (select id from exams where code = 'sca');
  sv uuid := (select sv.id from station_versions sv join stations s on s.id = sv.station_id
              where s.exam_id = exam and sv.status = 'published' order by sv.created_at limit 1);
  payload jsonb := '${GREEN_PAYLOAD}';
BEGIN
  INSERT INTO attempts (id, kind, user_id, exam_id, station_version_id, status, started_at, completed_at)
    VALUES ('${a}', 'practice', u, exam, sv, 'evaluated', now() - interval '20 minutes', now() - interval '5 minutes');
  INSERT INTO assessment_results (id, attempt_id, framework_id, policy_version, model_used, payload, scored_at)
    VALUES (gen_random_uuid(), '${a}', 'sca', 'e2e-fixture', 'fixture', payload, now());
END $$;`);
  return a;
}

/**
 * What a spoken, marked exam station leaves behind: an evaluated exam-slot
 * attempt with a result, and the slot completed (the room is skipped here, so
 * the api marked the slot "skipped" and nothing could be marked or decided).
 */
export function seedMarkedSlotAttempt(slotId: string): void {
  const attempt = randomUUID();
  psql(`
DO $$
DECLARE
  s record;
  payload jsonb := '${GREEN_PAYLOAD}';
BEGIN
  SELECT sl.id, sl.org_id, sl.trainee_id, sl.station_version_id, st.exam_id INTO s
    FROM slots sl JOIN station_versions sv ON sv.id = sl.station_version_id JOIN stations st ON st.id = sv.station_id
    WHERE sl.id = '${slotId}';
  INSERT INTO attempts (id, kind, user_id, org_id, exam_id, station_version_id, slot_id, status, started_at, completed_at)
    VALUES ('${attempt}', 'exam_slot', s.trainee_id, s.org_id, s.exam_id, s.station_version_id, s.id, 'evaluated', now() - interval '20 minutes', now() - interval '5 minutes');
  INSERT INTO assessment_results (id, attempt_id, framework_id, policy_version, model_used, payload, scored_at)
    VALUES (gen_random_uuid(), '${attempt}', 'sca', 'e2e-fixture', 'fixture', payload, now());
  UPDATE slots SET status = 'completed' WHERE id = s.id;
END $$;`);
}

/**
 * An SCA plan on sale (local runs only), so the Payments tab offers one. Pricing a plan through the api
 * creates Stripe prices, which a run has no keys for, so a fresh database gets the row the
 * staff pricing screen would leave, with a placeholder price id. Skipped when one is on sale.
 */
export function ensureScaPlanOnSale(): void {
  // Columns of api/app/features/billing/models.py `Plan`.
  psql(`
INSERT INTO plans (id, code, stripe_price_id, exam_code, amount_pence, currency, duration_days, active)
  SELECT gen_random_uuid(), 'e2e_sca', 'price_e2e_sca', 'sca', 2900, 'gbp', 90, true
  WHERE NOT EXISTS (SELECT 1 FROM plans WHERE exam_code = 'sca' AND active)
  ON CONFLICT (code) DO UPDATE SET active = true;`);
}

/**
 * A matched peer session already in `phase`, with `doctor` and `patient` both
 * joined. Matching needs two browsers and the api's worker; the room's layout
 * needs neither. Returns the session id; `endPeerSession` removes it.
 */
export function seedPeerSession(doctor: string, patient: string, stationVersionId: string, phase: "preparation" | "consultation"): string {
  const id = randomUUID();
  const user = (email: string) => `(select id from users where email = '${email.replace(/'/g, "''")}')`;
  psql(`
INSERT INTO practice_sessions (id, exam_id, doctor_user_id, patient_user_id, station_version_id, status, current_phase,
    phase_ends_at, started_at, doctor_joined_at, patient_joined_at, preparation_started_at, doctor_accepted_at, patient_accepted_at)
  VALUES ('${id}', (select id from exams where code = 'sca'), ${user(doctor)}, ${user(patient)}, '${stationVersionId}', 'active', '${phase}',
    now() + interval '20 minutes', now(), now(), now(), now(), now(), now());`);
  return id;
}

export function endPeerSession(id: string): void {
  psql(`DELETE FROM practice_sessions WHERE id = '${id}';`);
}

/**
 * An account whose sign-up exam is `signup` while its only live grant is for `held`: someone who
 * registered for one exam and then bought another. The api's `register` takes no exam, so the
 * sign-up exam is written the way `ChooseExam` would leave it. Returns the user's id.
 *
 * Fails, naming the seed, when the user or either exam is missing: without that the UPDATE and
 * INSERT touch no rows and the journey would test nothing (a fresh database needs
 * `scripts/seed_platform.py`, which publishes the exams).
 *
 * `held` and `signup` go into the SQL as written, so pass literal exam codes.
 */
export function seedSignedUpForButHolding(email: string, held: string, signup: string): string {
  const quoted = email.replaceAll("'", "''");
  const exam = (code: string) => `(select id from exams where code = '${code}' and owner_kind = 'platform')`;
  psql(`
DO $$
DECLARE
  u uuid := (select id from users where email = '${quoted}');
  held_exam uuid := ${exam(held)};
  signup_exam uuid := ${exam(signup)};
BEGIN
  IF u IS NULL THEN RAISE EXCEPTION 'e2e seed signed-up-but-holding: no user %', '${quoted}'; END IF;
  IF held_exam IS NULL THEN RAISE EXCEPTION 'e2e seed signed-up-but-holding: no platform exam "${held}" (run api/scripts/seed_platform.py)'; END IF;
  IF signup_exam IS NULL THEN RAISE EXCEPTION 'e2e seed signed-up-but-holding: no platform exam "${signup}" (run api/scripts/seed_platform.py)'; END IF;
  UPDATE users SET exam_code = '${signup}' WHERE id = u;
  INSERT INTO entitlements (id, user_id, exam_id, source, starts_at, created_at, updated_at)
    VALUES (gen_random_uuid(), u, held_exam, 'purchase', now(), now(), now());
END $$;`);
  return psql(`select id from users where email = '${quoted}';`);
}
