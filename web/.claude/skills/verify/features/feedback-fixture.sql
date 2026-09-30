-- Replace the three ids per exam with marked attempts and published rubric versions from your own local DB:
--   select a.id, e.code, r.rubric_version_id from attempts a join exams e on e.id=a.exam_id join assessment_results r on r.attempt_id=a.id;
-- Local-only fixture: an institution owned by the @example.com test account,
-- with one sitting per consumer exam, each slot bound to an already-marked attempt.
DO $$
DECLARE
  test_user uuid := (select id from users where email='e2e-marking-3@example.com');
  org uuid := gen_random_uuid();
  sitting uuid; circuit uuid; slot uuid; copy uuid;
  row record;
BEGIN
  INSERT INTO organizations (id, slug, name) VALUES (org, 'verify-rubrics', 'Verify Rubrics (local)');
  INSERT INTO memberships (id, org_id, user_id, role) VALUES (gen_random_uuid(), org, test_user, 'admin');
  INSERT INTO trainees (id, org_id, email) VALUES (gen_random_uuid(), org, 'e2e-marking-3@example.com');
  FOR row IN
    SELECT * FROM (VALUES
      ('SCA', 'e8cd9b0c-568e-4cd2-8146-e02031e3b078'::uuid, 'cbe3c59b-de3d-46f0-a8ee-7e02d33211ce'::uuid),
      ('PLAB', 'db3ab552-1865-4005-8b1f-db6fd2087e91'::uuid, '26275df3-c486-4d22-9a03-f835ac5123e1'::uuid),
      ('CASC', '195ff539-9a86-41af-a99d-1a45a070f238'::uuid, '248895ee-422c-4db3-88cb-4b2d41b36893'::uuid),
      ('Ortho', 'cecd471d-b30c-47e0-a0c1-9c26c1a36305'::uuid, 'b7dd2fa4-7a85-4939-9b8f-1b1d7ce78246'::uuid)
    ) AS fixture(label, attempt_id, rubric_version_id)
  LOOP
    sitting := gen_random_uuid(); circuit := gen_random_uuid(); slot := gen_random_uuid();
    INSERT INTO sittings (id, org_id, name, rubric_version_id) VALUES (sitting, org, row.label || ' sitting', row.rubric_version_id);
    INSERT INTO circuits (id, sitting_id, org_id, name) VALUES (circuit, sitting, org, row.label || ' circuit');
    INSERT INTO circuit_stations (id, circuit_id, position, station_version_id)
      SELECT gen_random_uuid(), circuit, 0, station_version_id FROM attempts WHERE id = row.attempt_id;
    INSERT INTO circuit_trainees (id, circuit_id, trainee_id, position) VALUES (gen_random_uuid(), circuit, test_user, 0);
    INSERT INTO slots (id, circuit_id, org_id, slot_index, trainee_id, station_version_id, status)
      SELECT slot, circuit, org, 0, test_user, station_version_id, 'completed' FROM attempts WHERE id = row.attempt_id;
    -- A copy of the marked consumer attempt, as an exam-slot attempt of this org;
    -- the original practice attempt is left untouched.
    copy := gen_random_uuid();
    INSERT INTO attempts (id, kind, user_id, org_id, exam_id, station_version_id, slot_id, definition, definition_frozen_at, status, started_at, completed_at)
      SELECT copy, 'exam_slot', user_id, org, exam_id, station_version_id, slot, definition, definition_frozen_at, status, started_at, completed_at FROM attempts WHERE id = row.attempt_id;
    INSERT INTO assessment_results (id, attempt_id, framework_id, policy_version, model_used, payload, scored_at)
      SELECT gen_random_uuid(), copy, framework_id, policy_version, model_used, payload, scored_at FROM assessment_results WHERE attempt_id = row.attempt_id;
  END LOOP;
END $$;
