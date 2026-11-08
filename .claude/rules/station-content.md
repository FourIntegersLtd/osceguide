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
- **Every path that adds to or starts from a set entry re-validates the version against the set's
  exam** (`_ensure_usable_versions`: exists, published, same `exam_id`). Create, replace and
  `start_entry_attempt` each check; checking only on write left stored cross-exam entries sittable
  under the wrong grant, and a `PATCH` of a station's `exam_id` reopened it (`test_a_set_cannot_be_built_from_another_exams_station`,
  `test_a_stored_entry_whose_station_is_now_another_exams_cannot_be_attempted`). A debrief starts no
  station and is deliberately unguarded.
- **A learner builds a set but never changes or deletes it**: `PATCH`/`DELETE /me/station-sets/{id}` are
  `PlatformAdmin` (a learner gets `forbidden`, 403); create, run, debrief and flag stay the learner's.
- A set entry's `station_title` is null until the entry has been sat (`attempts > 0`): screens show
  "Station N" (`stationLabel`), and Edit Session adds a random unsat station, never one picked by
  title. A trial learner's create or edit is capped at the free stations left
  (`trial_station_limit`, `GET /me/station-sets/allowance`), counted by station minus ones already sat.
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

## What a failure looks like here
- A station's scenario or patient material reaching a trainee before the attempt.
- A read widened to make a screen work.
- A second open draft, or a screen that assumes a station survives deleting its last version.
- A published station with no `patient_information` or template, so its attempts are never marked.
- Content models are literals checked by `api/tests/guards/test_model_retirements.py`. Claude is the first
  provider, OpenAI the second: claude-sonnet-5-5 for station generation and import (`stations/station_ai.py`),
  JSON generation (`generation/service.py`) and podcast scripts (`podcast_script.py`, via
  `slide_narration.complete(claude_first=True)`); claude-haiku-5-5 splits peer transcripts into turns
  (`peer_practice/diariser.py`, matched sonnet and gpt-6-luna on 3 samples); gpt-6.1-sol / gpt-6-luna /
  gpt-transcribe answer when Claude has no key or fails. `app/core/llm.py` is the one home of model calls
  (`claude_reply`, `openai_reply`, `first_that_answers`, `json_object`): cached system, no temperature, no `tool_choice`,
  `output_config` carries both `format` and `effort`; `effort="low"` for podcast scripts (25s, not 200s) and the diariser.
  Models are `core.llm` constants (`CLAUDE_*`, `OPENAI_STRONG` gpt-6.1-sol, `OPENAI_FAST` gpt-6-luna); `openai_reply` takes `messages`, optional `max_tokens`/`reasoning_effort`/`response_format`, and raises `LlmReplyUnusable` on an empty reply so the fall-through happens. `slide_narration.complete` defaults Claude to 16000 tokens at `effort="low"` (the fact checker and second reader depend on it: a cut-off raises and silently hands the check to the writer's own model).
  The sync `slide_narration.complete` runs them on a private event loop (never `asyncio.run`: it unsets the thread's loop). Claude 5.5
  answers 400 to a forced `tool_choice` and any `temperature` but 1; its thinking counts in `max_tokens` (give
  16000+); `output_config` schemas compile only to about 7KB (the station schemas are 0.3-2.4KB). A bigger
  schema goes through the engine's `ask_by_tool` instead. `gpt-6.1-sol` takes no `reasoning_effort` of `none`.
- A test that builds `Settings(openai_api_key=...)` still reads `ANTHROPIC_API_KEY` from `.env`: pass
  `anthropic_api_key=""` to mean "no Claude key", or the "OpenAI only" case silently runs on Claude.
- **The library page and exam lists are cached (`core.cache`, `library_cache_seconds`).** `browse_library` caches the page whole per exam (it carries nothing per person) under `library:page:...:v{version}`; a plan-limited person's window is per person, so that read is not cached. `first_station_ids` is cached as the full ordered list (`library:first:{exam}`), exclusions and limit applied after. `catalog.exam_codes` / `org_exam_ids` use the `catalog` version. Any new write that changes a platform station's title, status, approval or current version must call `stations.service.bump_library(session, station)`; any exam or programme write `catalog.service.bump_catalog(session)`. Both run after commit. HTTP tests do not flush cache ops (the test session override only flushes events): call `cache.flush_cache_ops(db_session)` after a service write, and point `cache.get_redis`/`KEY_PREFIX` at `seat_redis` (see `tests/http/test_library_cache.py`). Offline writers (`app/migration`, seed scripts) bump nothing; the TTL covers them.
- A station photo upload takes at most `domain_photos.MAX_FILES` (10) files per request, refused whole as `invalid_photo`.

- The marking scheme builder (`web/src/capabilities/authoring/rubrics`) edits schemaVersion 3 only; `readScheme` sends anything else to the JSON view. TS unions in `schemeModel.ts` must match the api constants (`test_shared_vocabulary.py`). Removing a scale level also strips its descriptors and pass rules (`removeLevel`).
- Scheme builder UI traps: the outline keeps its picked row as an index, so every edit that moves rows goes through `edit(next, change)` with `remapFocus` (never `onScheme` directly); below xl the detail is a sheet, so row inputs must not set focus (only Details opens it). Rows carry `data-path` (`outline[i]`, `.title`, `.competencies[j].label`) and a problem click sends a `RevealRequest` so the outline expands the domain, opens the detail and focuses the field. JSON typed in Advanced lives in `SchemeBuilder` (`jsonText`), not in the disclosure: it survives tab and scheme changes, counts as unsaved for the leave guard and turns Save off until applied or discarded. `PopupMenu`, `useDismissOnOutside` and `useMediaQuery` are foundation; row-input labels carry the row ("Title of domain 2"), so match with a regex or `.first()`.
- **Board-matched authoring screens** (`docs/institution-overhaul/boards`, specs `web/e2e/assess/board-*.spec.ts`): use `boardKit` tokens and `foundation/ui/BoardFields` (`BoardSelect`, `BoardTextarea`, `BoardCheckbox`), since `consoleDesign.test.ts` bans raw `<select>`, `<textarea>` and checkbox inputs. Traps: `text-assess-*` carries a 1.5 line-height that only `!leading-[normal]` beats; the board's fold summary is content-box (`box-content min-h-[24px]`); the app scrolls inside its shell, so compare at viewport height 2400; the create-station template list is oldest first (pick "(v2)"); `RESEED=1` rebuilds the cached exams org. The board edits a draft exam, so the settings spec creates one.
- LayoutBuilder board (`LayoutBuilder.dc.html`) mirrors the seeded ortho exam from `web/e2e/support/seed-layout-builder.ts` (5 layouts, draft v3, published v2) and the builder markup under `stations/templates/builder/`; redraw it from the rendered DOM when the builder changes, and note tab 2 (new) sits 20px lower than tabs 3-4 in the app, so the board carries a per-state gap rather than a mask.

- A request that holds its transaction open across a model call (generation, station autogenerate) calls `core.jobs.allow_long_idle(session)` first; the database drops a transaction idle over 1 min. `tests/repository/test_allow_long_idle.py` proves it, the route tests read the setting inside the mocked model call.
- StructureBuilder `readOnly` freezes only the field panels (`Frozen` fieldsets) and the drag sensors; the Build/Preview tabs and section navigation must stay live on a published version. Never wrap the whole builder in a disabled fieldset.
- Builder structure: `StructureBuilder` is only the Build/Preview switch; `BuilderBoard` is the three-column Build body and `SectionSettingsDialog` the modal. `SectionStage` takes `readOnly` and disables only edit controls (details, fields, add field); Previous/Next and undo/redo stay live.
- A station whose template's candidate-audience section holds text has no flat Reading brief: `StationDetail` hides `BriefEditor` and the "no candidate brief" warning and notes that section (`filledCandidateSection`: any candidate section, mirroring the server's `sections_for`, so examiner/faculty/debrief/hidden blocks never count and `false` or `[""]` count as written). A blank candidate section keeps the box, because the runner falls back to the flat brief. `_json_completion`, `_titled`, deck and podcast take a required `session: AsyncSession | None` (no default; `None` = no transaction held, nothing to lift, as `service_produce` passes for deck/podcast) and lift the idle limit (`MODEL_CALL_IDLE_SECONDS`, 25 min); any job awaiting a model, transcriber or diariser with a transaction open calls `allow_long_idle`.
- Approval gates the platform library only (`owner_kind='platform'`: the library index and `repository_library.py`). An org's own stations never wait on platform staff: the stations table shows the pill and the Approve button only in the platform scope (`showApproval`), and `test_an_org_station_never_waits_on_platform_approval` proves a published, unapproved org station lists and joins a circuit.
- Authoring and staff-media rows keep one inline primary and put the rest in `AuthoringActionMenu` (`capabilities/authoring/parts`, wraps `ActionMenu`; `write` items are hidden from readers). A menu item has no busy spinner, so it is disabled while any action runs.

- Authoring sentences that name people, scheduling or circuits come from `capabilities/authoring/lib/authoringCopy.ts` (pure, takes `AssessWords`), never literals; hire says Candidate brief and blocks Publish with "Publish needs a candidate brief." Pure modules import `assess-words/vocabulary`, not the index (the index pulls TSX the node test loader cannot parse).
