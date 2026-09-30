---
name: verify-institution
description: How to prove a change to the institution arm works — sittings and circuits, roster, tenancy and org admin, reviews and the result decision workflow, and the domains/assess and domains/platform screens. Use before calling any institution change done.
---

# Verify the institution arm

Pick the **lowest level that can see your change**, run it, and report the
command and its output.

| Your change | Minimum proof |
|---|---|
| A backend rule or route (roster, tenancy, decisions, circuit edit) | Level 1 |
| A permission, a role, anything tenant-scoped | Level 1 + `tests/security` |
| A screen under `domains/assess` or `domains/platform` | Level 1 if the backend changed, then Level 2 |
| Circuit clock, overrides, running a circuit | Level 1 + Level 2 + the circuit flow in `verify-voice-station` |
| A response schema | Level 1, regenerate types, then Level 2 |

## Level 1 — backend tests (~4 min, needs the docker services)

```bash
cd api
docker compose up -d            # Postgres :5433, Redis :6380; without them DB tests skip
LIVEKIT_AGENT_NAMESPACE= poetry run pytest -q \
  tests/unit/test_sittings_domain.py tests/unit/test_sittings_domain_edit.py \
  tests/unit/test_sittings_domain_run.py tests/unit/test_roster_domain.py \
  tests/unit/test_tenancy_domain.py tests/unit/test_results_domain.py \
  tests/unit/test_reviews_domain.py \
  tests/repository/test_circuit_run.py tests/repository/test_circuit_jump_race.py \
  tests/repository/test_circuit_overrides.py tests/repository/test_sitting_completion.py \
  tests/repository/test_tenancy_repository.py \
  tests/http/test_sittings_routes.py tests/http/test_sitting_edit_routes.py \
  tests/http/test_circuit_override_routes.py tests/http/test_circuit_tokens.py \
  tests/http/test_roster_routes.py tests/http/test_roster_edit_routes.py \
  tests/http/test_append_trainees_routes.py tests/http/test_tenancy_routes.py \
  tests/http/test_invitations.py tests/http/test_results_routes.py \
  tests/http/test_reviews_routes.py tests/http/test_live_board.py \
  tests/http/test_org_read_models.py tests/http/test_sitting_report.py \
  tests/http/test_sitting_readout_routes.py \
  tests/security/test_membership_role_escalation.py
```

457 passed on 2026-09-25. Empty `LIVEKIT_AGENT_NAMESPACE` because a local
`.env` that sets it fails the circuit-token tests without anything being broken.

After a schema change: `make openapi`, then in platform-web
`npm run platform:types` and `npm run types`, then `npm run ci`.

## Level 2 — the screen in a real browser

Use platform-web's `verify` skill (`web/.claude/skills/verify/`):
`doctor.mjs` until it says `ready`, then drive the screen with its harness.
`features/institution.md` has the handles for the dashboard, sittings and
authoring. The test account `walkthrough@example.com` owns `kings` and is
institution admin of `st-marys`; write data only there, and say so in the run log.

Check the request count too: a screen that renders right while looping
requests is still broken. Then run `node scripts/smoke.mjs` if you touched an `api.ts`.

## Traps

- `trainee_id` means two things: circuit slots use `users.id`, result decisions use `trainees.id`.
- A platform admin reads any organisation for support but holds none of its
  powers (`OrgAdmin` is `allow_platform_admin=False`). A 403 from the staff
  console on an org-admin route is correct.
- Exam-mode observers are subscribe-only; training-mode supervisors may publish.
- A circuit's clock is never extended for one candidate's `extra_reading_percent`.
- Adding a candidate to a live exam circuit is refused `not_permitted_in_mode` (D7). That is intended.
- `/authoring` redirects to `/authoring/stations`; `<main>` is empty until the
  tablist appears. It is not a broken page.
