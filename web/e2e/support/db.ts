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

const CONTAINER = process.env.E2E_PG_CONTAINER ?? "platform-api-postgres-1";

function psql(sql: string): string {
  assertLocalApi();
  return execFileSync("docker", ["exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "osce_platform", "-At", "-v", "ON_ERROR_STOP=1"], {
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
  payload jsonb := '{"global_skills": {"structures_consultation": {"score": "G", "supporting_phrase": "Shall we start with what brought you in?", "explanation": "Clear opening."}}}';
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
  payload jsonb := '{"global_skills": {"structures_consultation": {"score": "G", "supporting_phrase": "Shall we start with what brought you in?", "explanation": "Clear opening."}}}';
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
