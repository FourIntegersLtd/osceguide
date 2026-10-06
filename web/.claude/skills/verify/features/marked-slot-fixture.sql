-- Local-only, self-contained (the local DB has no marked attempts): walkthrough@example.com gets one marked
-- SCA practice attempt (...b5302, learner feedback) and org verify-b53 whose slot ...b5301 carries a marked
-- exam_slot copy (...b5303, examiner review). Teardown: marked-slot-teardown.sql. Driven by .verify/fix-B53.mjs.
DO $$
DECLARE
  u uuid := (select id from users where email='walkthrough@example.com');
  exam uuid := (select id from exams where code='sca');
  sv uuid := '34ac6ea7-5117-48c9-b078-35524c44d33b';
  org uuid := '00000000-0000-4000-8000-0000000b5300';
  sitting uuid := gen_random_uuid(); circuit uuid := gen_random_uuid();
  slot uuid := '00000000-0000-4000-8000-0000000b5301';
  practice uuid := '00000000-0000-4000-8000-0000000b5302';
  copy uuid := '00000000-0000-4000-8000-0000000b5303';
  payload jsonb := '{"global_skills": {"structures_consultation": {"score": "G", "supporting_phrase": "Shall we start with what brought you in?", "explanation": "Clear opening."}}}';
BEGIN
  INSERT INTO organizations (id, slug, name) VALUES (org, 'verify-b53', 'Verify B53 (local)');
  INSERT INTO memberships (id, org_id, user_id, role) VALUES (gen_random_uuid(), org, u, 'admin');
  INSERT INTO sittings (id, org_id, name, rubric_version_id) VALUES (sitting, org, 'B53 sitting', '5d77bdf4-97e0-47ff-af5b-739d7328cb4d');
  INSERT INTO circuits (id, sitting_id, org_id, name) VALUES (circuit, sitting, org, 'B53 circuit');
  INSERT INTO circuit_stations (id, circuit_id, position, station_version_id) VALUES (gen_random_uuid(), circuit, 0, sv);
  INSERT INTO circuit_trainees (id, circuit_id, trainee_id, position) VALUES (gen_random_uuid(), circuit, u, 0);
  INSERT INTO slots (id, circuit_id, org_id, slot_index, trainee_id, station_version_id, status) VALUES (slot, circuit, org, 0, u, sv, 'completed');
  INSERT INTO attempts (id, kind, user_id, exam_id, station_version_id, status, started_at, completed_at)
    VALUES (practice, 'practice', u, exam, sv, 'evaluated', now() - interval '20 minutes', now() - interval '5 minutes');
  INSERT INTO attempts (id, kind, user_id, org_id, exam_id, station_version_id, slot_id, status, started_at, completed_at)
    VALUES (copy, 'exam_slot', u, org, exam, sv, slot, 'evaluated', now() - interval '20 minutes', now() - interval '5 minutes');
  INSERT INTO assessment_results (id, attempt_id, framework_id, policy_version, model_used, payload, scored_at) VALUES
    (gen_random_uuid(), practice, 'sca', 'b53-fixture', 'fixture', payload, now()),
    (gen_random_uuid(), copy, 'sca', 'b53-fixture', 'fixture', payload, now());
END $$;
