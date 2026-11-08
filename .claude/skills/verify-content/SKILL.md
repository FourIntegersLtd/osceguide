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
cd api
docker compose up -d            # Postgres :5433, Redis :6380; without them DB tests skip
# domain + repository (~5s)
poetry run pytest -q \
  tests/unit/test_stations_domain.py tests/unit/test_station_validator.py \
  tests/unit/test_stations_candidate_content.py tests/unit/test_station_sets_domain.py \
  tests/unit/test_generation_normalizers.py tests/unit/test_generation_profile_resolve.py \
  tests/unit/test_media_object_urls.py tests/http/test_media_signed_urls.py \
  tests/http/test_station_signed_urls.py tests/repository/test_material_reindex.py \
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
  tests/http/test_station_set_trial_routes.py \
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

- Media links are signed on read and stripped on write. A test of media content must expect `X-Amz-Signature` in a gated link and a plain one under `Four+Integers+Ltd/` and `teaching_videos/v2/pictures/`.
- **A station's scenario never reaches the browser before an attempt.** The
  org station list strips the patient's material for trainees
  (`stations/domain_content.py`). A screen missing a field is not a reason to widen a read.
- **Library stations are adopted by reference**, not copied.
- Station authoring screens are driven with `web/.verify/fixlib.mjs` (`api()` for a signed-in
  fetch, `newStation()` for a fresh platform station, `dropExpected()` for the 409s a script
  provokes on purpose and the external `ERR_NAME_NOT_RESOLVED`). The list keeps `?status=` and
  `?station=<id>` in the address; a saved new station lands on `?station=<id>`. `scripts/smoke.mjs`
  needs `PLATFORM_API_URL=http://127.0.0.1:8013` when the api is not on :8002.
- A community question's title is the first line of its body; the backend takes a title.
- Station images are a plain `<img>`, not `next/image`: their hosts are not configured.
- Media facets read `content.specialty`; `MediaRead.specialty` exists but nothing writes it yet.
- A row action the server refuses for a status (publish without a rubric, retire a draft)
  is not offered; a failed confirm shows its reason inside
  the dialog (`error={action.error}`). Screens for exams and staff media:
  platform-web `verify/features/content-authoring.md`.
- **Media publish is gated on the pipeline**: publishing while `production.is_running` is
  `media_being_produced` (409); `POST /media/{id}/unpublish` returns a published item to draft
  (the only way to delete it); `POST /media/{id}/unlock` marks a stuck `running` item failed
  (`av_not_running` if it is not running). Staff screens confirm each of these.
- The moderation queue pages by cursor (`GET /platform/community/moderation?cursor=`); a test
  must create more rows than the page limit to prove it. The brief carries `created_at`,
  `started_at`, `server_time` so the station clock does not trust the browser.
- A published media item's content is fixed (`media_not_editable`); only title, summary and
  exam save.
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
- **A before/after of a model call** (generation, import, podcast, diarisation): call the function with
  `Settings(openai_api_key=..., anthropic_api_key="")` for the OpenAI side (an omitted key is read from
  `.env`, so the "OpenAI" run is really Claude), run it with `PYTHONPATH=.`, and send output to a file:
  a podcast script takes ~50-70s and JSON station drafts ~60s.
- Live call for a Claude path: a script in the scratchpad (not `$TMPDIR`, whose stray `http.py` shadows the stdlib), run with `PYTHONPATH=.`; wrap `anthropic.resources.messages.AsyncMessages.create` to print `usage`. Podcast script at `effort=low`: ~25s, 2.8k output tokens; diariser: ~1.5s.

## Marking scheme builder traps (web)
- `eslint .` hangs on stray gitignored `.next-*` dirs: run `npx eslint src scripts`.
- `check:polling` flags any `setTimeout(` near an api call; defer with `requestAnimationFrame`.
- `consoleDesign.test.ts` rejects a raw `<textarea>`: use the foundation `Textarea`.
- The builder's tablist is "Marking scheme" (Domains, Scale, Pass rule, Feedback, Advanced, Trial mark, Versions); names carry problem counts, so match `/Trial mark$/`.
- Proof that a published version is untouched: `select md5(string_agg(md5(structure::text), ',' order by id::text)) from rubric_versions where status='published'` before and after.
- macOS: `sed -i ''`; no `timeout`.

- Scheme builder walk: domains start collapsed except the first, so a script that counts or fills competency inputs must open the caret or read the outline counts; the detail panel is `getByTestId("outline-detail")`, not the "Details" buttons. A preset switch only asks to confirm when level descriptions exist. A station rule "every domain passes" needs a domain pass rule, or the scheme is blocked. A raw scheme (cannot show) is made by putting `advanced.raw` through the JSON editor (`web/.verify/scheme-raw.mjs`).

- Scheme builder fixes probe: `web/.verify/phase-b-fixes.mjs` (local, gitignored) checks the narrow-screen sheet, row-move focus, menu keyboard, tab arrows, pass-rule sentence and unapplied JSON. `rubric-proof.mjs <PLAB|Simulated|CASC|Orthopaedic>` takes the exam as an argument: a loop that runs `rubric-proof PLAB.mjs` fails with MODULE_NOT_FOUND. Its published notice reads "Version N is published."
- Board-match specs (`e2e/assess/board-*.spec.ts`): run one per call on your own dev port with `E2E_REUSE_SERVER=1 VERIFY_WEB_URL=...`; a run over 120s is backgrounded, so redirect to a file and wait on it. Scores can drift when another change to a shared kit component (FoldSection, StationInstanceContentPanel, B2CPageHeader) lands: re-run before blaming your own screen.
- A published template version is `/versions/1` of the demo-walkthrough seed template and the list links its draft `/versions/2`; `walkthrough@example.com` is the harness account. On desktop the first `Sections` tablist is the hidden phone strip: click the `aside` outline's tabs.
