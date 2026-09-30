-- Local-only: org verify-r3 owned by walkthrough@example.com, one SCA sitting with one slot
-- (id 00000000-0000-4000-8000-000000000003) and no attempt. Needs no stations or marked attempts.

DO $$
DECLARE
  test_user uuid := (select id from users where email='walkthrough@example.com');
  exam uuid := (select id from exams where code='sca');
  org uuid := gen_random_uuid(); station uuid := gen_random_uuid(); station_version uuid := gen_random_uuid();
  sitting uuid := gen_random_uuid(); circuit uuid := gen_random_uuid(); slot uuid := '00000000-0000-4000-8000-000000000003';
BEGIN
  INSERT INTO organizations (id, slug, name) VALUES (org, 'verify-r3', 'Verify R3 (local)');
  INSERT INTO memberships (id, org_id, user_id, role) VALUES (gen_random_uuid(), org, test_user, 'admin');
  INSERT INTO stations (id, owner_kind, org_id, exam_id, title, status) VALUES (station, 'org', org, exam, 'R3 fixture station', 'published');
  INSERT INTO station_versions (id, station_id, version, content, status) VALUES (station_version, station, 1, '{}'::jsonb, 'published');
  INSERT INTO sittings (id, org_id, name, rubric_version_id) VALUES (sitting, org, 'R3 sitting', 'cbe3c59b-de3d-46f0-a8ee-7e02d33211ce');
  INSERT INTO circuits (id, sitting_id, org_id, name) VALUES (circuit, sitting, org, 'R3 circuit');
  INSERT INTO circuit_stations (id, circuit_id, position, station_version_id) VALUES (gen_random_uuid(), circuit, 0, station_version);
  INSERT INTO circuit_trainees (id, circuit_id, trainee_id, position) VALUES (gen_random_uuid(), circuit, test_user, 0);
  INSERT INTO slots (id, circuit_id, org_id, slot_index, trainee_id, station_version_id, status) VALUES (slot, circuit, org, 0, test_user, station_version, 'completed');
END $$;
