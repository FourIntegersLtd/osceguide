---
name: verify-content
description: How to prove a change to content works — the station library and templates, station authoring, AI generation, study media and podcasts, practice sets, community, the marketplace, peer practice, CV reading and the public site's backend. Use before calling any content change done.
---

# Verify content

Pick the **lowest level that can see your change**, run it, and report the
command and its output.

| Your change | Minimum proof |
|---|---|
| A domain rule (validation, audiences, access to a body, queue pairing) | Level 1, and show the rule is called |
| What a read returns, especially to a trainee | Level 1 + read the response as that role |
| A screen in `stations`, `authoring`, `media`, `community`, `peer-practice` | Level 1 if the backend changed, then Level 2 |
| Generation or media production | Level 1 + Level 2 with `make worker` running |
| An import script | Its default dry run against the local database |

## Level 1 — backend tests (needs the docker services)

```bash
cd backend/platform-api
docker compose up -d            # Postgres :5433, Redis :6380; without them DB tests skip
# domain + repository (~5s)
poetry run pytest -q \
  tests/unit/test_stations_domain.py tests/unit/test_station_validator.py \
  tests/unit/test_stations_candidate_content.py tests/unit/test_station_sets_domain.py \
  tests/unit/test_generation_normalizers.py tests/unit/test_generation_profile_resolve.py \
  tests/unit/test_media_domain.py tests/unit/test_media_trial_access.py \
  tests/unit/test_community_domain.py tests/unit/test_marketplace_domain.py \
  tests/unit/test_cv_domain.py tests/unit/test_public_site_domain.py \
  tests/unit/test_peer_practice_domain.py tests/unit/test_peer_station_material.py \
  tests/unit/test_peer_transcript_diarisation.py tests/unit/test_b2c_deck_slides.py \
  tests/repository/test_marketplace_claim_race.py tests/repository/test_media_index.py \
  tests/repository/test_material_index.py tests/repository/test_material_reindex.py \
  tests/repository/test_practice_queue_race.py
# routes (minutes)
poetry run pytest -q \
  tests/http/test_stations_routes.py tests/http/test_station_template_routes.py \
  tests/http/test_station_flags_routes.py tests/http/test_station_photo_routes.py \
  tests/http/test_station_autogenerate_routes.py tests/http/test_library_station_reads.py \
  tests/http/test_platform_stations_routes.py tests/http/test_platform_user_station_routes.py \
  tests/http/test_station_sets_routes.py tests/http/test_station_set_edit_routes.py \
  tests/http/test_generation_routes.py tests/http/test_media_routes.py \
  tests/http/test_media_production_routes.py tests/http/test_community_routes.py \
  tests/http/test_cv_routes.py tests/http/test_public_site_routes.py \
  tests/http/test_peer_practice_routes.py tests/http/test_peer_recording.py \
  tests/http/test_audiences.py
```

157 + 223 passed on 2026-09-25 (~4 min in all); `test_peer_practice_routes.py`
alone grew to 30 (accept/decline handshake, 2026-09-26). Run the two halves
separately; one combined run was killed once.

## Level 2 — the real thing

- **A screen:** platform-web's `verify` skill (`doctor.mjs` until `ready`, then
  its harness). The rubric builder has `features/rubric-builder.md`; for any other
  content screen, write one the first time you drive it, in the same four sections.
- **Generation and media production:** `make start` and `make worker`, with
  `OPENAI_API_KEY` (and `CARTESIA_API_KEY` for audio; `ffmpeg` on `PATH` for
  slide video). Trigger it as platform staff, then read the stored `media`
  row's `content.status`, not the log line.
- **Imports:** `poetry run python scripts/import_b2c_all.py --only <step>`
  runs everything and rolls back by default. `--no-dry-run` commits; only
  ever against the local database.

## Traps

- **A station's scenario never reaches the browser before an attempt.** The
  org station list strips the patient's material for trainees
  (`stations/domain_content.py`). A screen missing a field is not a reason to widen a read.
- **Library stations are adopted by reference**, not copied.
- A community question's title is the first line of its body; the backend takes a title.
- Station images are a plain `<img>`, not `next/image`: their hosts are not configured.
- Media facets read `content.specialty`; `MediaRead.specialty` exists but nothing writes it yet.
- A migrated database is empty: seed it (`scripts/seed_platform.py`) before
  anything that files a station under an exam.
- **`tests/conftest.py`'s `override_get_session` reuses one `db_session` across every
  request in an HTTP test.** A request that fails — a 422, or any `AppError`
  with `persist_effects=False` (the default, every plain 409) — rolls that
  session back, which erases anything inserted directly through `db_session`
  in the test body (e.g. calling a service function and only `flush()`-ing,
  never `commit()`-ing) and expires every ORM attribute already read off it,
  so touching one later (`some_row.id` in an f-string) raises `MissingGreenlet`
  with a trace nowhere near the real cause. Capture any id you need later into
  a plain variable right after creating the row, and order requests so a
  success (which commits) happens before one you expect to fail.
