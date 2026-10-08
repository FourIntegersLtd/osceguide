---
paths:
  - "api/app/features/{stations,station_sets,generation}/**"
  - "api/scripts/{import_b2c_stations,seed_station_templates,link_stations_to_templates,export_station_generation_profiles}.py"
  - "api/app/migration/{stations,b2c_station_sources,load_stations}.py"
  - "web/src/capabilities/{stations,authoring}/**"
---
# Station content: what to know

Owner: `content-owner`. Proof: `verify-content`.

- **A station's scenario never reaches the browser before an attempt.** The patient's material is
  stripped for trainees (`stations/domain_content.py`). Never widen what a read returns to fix a
  screen.
- **One open draft per station.** `add_version` refuses a second (`draft_exists`), and deleting the
  last version deletes the station: a screen must not assume the station survives a delete.
- Stations are filed under an exam that has an owner (ADR 0017); audiences for anything social:
  ADR 0014. Station sets (mocks) have entry flags; sets are edited by revision (stale edits refused).
- A published station needs `patient_information` or a template layout, or its attempts render
  degraded and are never marked. Templates are platform-authored or copied (`station_template_copies`).
- Generation profiles and prompts are per exam in `exams.settings`; never branch on an exam code.
  Generation runs as background jobs (`make worker`); a screen must handle a failed job.
- Imports (`import_b2c_*`) default to a dry run against the local database. Real data never goes to
  staging (`app.migration` refuses under `APP_ENV=staging`).
- Search escapes wildcards (`test_search_escapes_wildcards`); lists are keyset-paged.
- Web: the authoring screens (`capabilities/authoring`) are many and deep; each load goes through
  `useAsync` + `AsyncBoundary`. Open authoring items: `web/docs/BACKLOG.md`.
  Browser handles: `web/.claude/skills/verify/features/content-authoring.md`, `rubric-builder.md`.
