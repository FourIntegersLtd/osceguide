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
