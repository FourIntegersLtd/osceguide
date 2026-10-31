---
paths:
  - "api/app/features/{tutor_memory,assistant}/**"
  - "assessment/packages/livekit_assistant_worker/**"
  - "assessment/tests/test_{assistant_worker,ui_guidance}*.py"
  - "web/src/capabilities/{onboarding,help}/**"
  - "web/src/foundation/livekit/guidance/**"
---
# Tutor and assistant: what to know

Owner: `attempt-engine-owner`. Proof: `verify-attempt-engine`. Athena is the voice assistant
(help, onboarding, dashboard, consulting-doctor); tutor memory is what she remembers.

- `livekit_assistant_worker` must not import `osce_assessment.runtime`, `.evaluation`, `.schemas`,
  `.catalog`, `.compat`, nor the assessment worker (`test_assistant_worker_boundaries.py`).
  Per-session-type decisions live only in its `modes.py` table; a string comparison against a
  session type anywhere else fails `test_assistant_worker_modes.py`.
- Instructions, greetings and speech-to-speech instructions arrive rendered in the bootstrap; the
  worker never sees a navigation label, product name or exam id
  (`test_assistant_worker_no_product_vocabulary.py`). Help sessions get the full FAQ rendered in
  (no FAQ search tool).
- UI guidance: one module per concern under `ui_guidance/`; pointers are written inline as
  `[POINT:x,y:Label]` and stripped in `GuidanceAgent`'s `tts_node`. Keep `ui_guidance/contracts.py`
  in step with the frontend `foundation/livekit/guidance` (`test_ui_guidance_contract_drift.py`
  reads the TypeScript). Announce a tool with `ctx.update` only when genuinely slow: the first update
  makes the call non-blocking and delays the sentence the user waits for (`ui_guidance/progress.py`).
- **"Returning" is decided by a `session_summary` tutor note, nothing else**
  (`tutor_memory/service_session.py` `greeting_for`). A dashboard session where the learner never
  spoke writes no note. Onboarding and consulting-doctor are discarded unread.
- `osce:open-athena` is heard by `LazyB2CHelpDock` until the dock has loaded and by `B2CHelpDock`
  afterwards; the lazy wrapper hands its pending launch over as `initialLaunch`. Keep both.
- The Athena doctor persona is reached from the debrief chooser ("Practice as the patient"), gated
  by the exam's `session_modes`; it needs a finished attempt.
- "I could not find that" in help: `search_material` has no score threshold, so suspect an
  un-reindexed help corpus (`POST /api/v1/admin/tutor-memory/reindex` as platform admin). Material
  is pgvector (ADR 0019).
- Onboarding opens on the step on screen: the session start's `extras.onboarding` is `{phase, scene}`
  and the server takes the scene **by index** from the pack (`service_content._onboarding_start`),
  never the client's text. Later steps are `scene_change` packets; `pause`/`resume` packets make the
  worker interrupt and hold any scene until resume (`handlers.wire_scene_changes`). Every demo scene
  needs `replies` and `model_answer` for text mode (`test_assistant_content.py`). Web and api deploy
  apart: the web reads scenes through `readScene`, which tolerates an api without those fields.
- Prompt injection: tutor input is untrusted (`tests/security/test_assistant_prompt_injection.py`).
- Written answers (`service_knowledge`, `service_community`) go through `assistant/service_llm.complete`: `core.llm.claude_reply` (Haiku 5.5, `effort: low`, cached system block; a max_tokens cut-off or refusal raises) then `core.llm.openai_reply` (`OPENAI_FAST`, `reasoning_effort=low`, `max_tokens` sent as `max_completion_tokens`, the whole conversation), chained by `first_that_answers`. No temperature or tool_choice; plain text only (structured replies use the engine's `ask_by_tool`). Test with `tests/support/llm_fakes.install_fake_sdks`; settings need both `anthropic_api_key` and `openai_api_key`.
- Dashboard `progress` counts only started, non-debrief attempts.

## What a failure looks like here
- A worker that learns a product, exam id or navigation label, or compares a session type outside `modes.py`.
- Paid material read to someone without a live entitlement.
- Tutor input trusted (prompt injection), or "returning" decided by anything but a `session_summary` note.
