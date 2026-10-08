# Published guides

Three plain-language guides are published as claude.ai artifacts and read by
people outside the code. Their sources live here so that a guide changes in the
same commit as the code it describes.

| Guide | Artifact | Watched paths |
|---|---|---|
| `platform-api-field-guide.html` | https://claude.ai/artifact/DdGp1umMckFMvBiiMaLPWQ | `api/app/features/*/models.py`, `api/app/features/*/router*.py`, `api/docs/DATA-MODEL.md`, `api/openapi.json`, `api/app/core/settings.py`, `AGENTS.md` |
| `how-osce-guide-works.html` | https://claude.ai/artifact/NHJAJk1fgc968xssyvn7F8 | `api/app/features/*/errors.py`, `api/openapi.json`, `api/app/core/lifecycle.py`, `api/app/features/sittings/*`, `api/app/features/roster/*`, `api/app/features/tenancy/*`, `api/app/features/results/*`, `api/app/features/reviews/*`, `api/app/features/sso/*`, `api/app/features/catalog/*`, `api/app/features/entitlements/*`, `api/app/features/billing/*`, `api/app/features/growth/*`, `api/app/features/identity/*`, `web/src/domains/*`, `web/src/surfaces/*`, `docs/EXPERIENCE-GAPS.md` |
| `how-the-voice-sessions-work.html` | https://claude.ai/artifact/2azMoTeSjqzxD9nBMHNT4p | `assessment/packages/*`, `assessment/hosting/*`, `assessment/k8s/*`, `api/app/features/voice/*`, `api/app/features/assistant/*`, `api/app/features/tutor_memory/*`, `api/app/features/attempts/router_worker.py`, `api/app/features/peer_practice/*`, `web/src/foundation/livekit/*`, `web/src/capabilities/attempt-runner/*`, `web/src/capabilities/station-runner/*`, `web/src/capabilities/debrief/*`, `web/src/capabilities/help/*` |

In a watched path, `*` matches across folders.

## Keeping them current

- **The field guide's table list is generated.** `api/scripts/build_field_guide.py`
  rewrites its `SCHEMA` block from `api/docs/DATA-MODEL.md` and `Base.metadata`.
  `make data-model` runs it with `--check`, so CI fails when the two drift. After a
  migration, run `cd api && PYTHONPATH=. poetry run python scripts/build_field_guide.py`.
- **The product guide's refusal rows are checked.** Every "what can go wrong" row
  in `how-osce-guide-works.html` carries `data-code="<error code>"`, and
  `make product-guide` fails when the api can refuse with a code the page has no
  row for, or a row cites a code the api no longer has. Write rows from
  `PYTHONPATH=. poetry run python scripts/build_product_guide.py inventory`, never
  from memory.
- **Everything else is prose.** A change to a watched path updates what it makes
  untrue in that guide, in the same commit, and sets the guide's "Checked
  against" line; or the change says why readers see no difference.
- **Republishing.** A source change is not live until it is republished. In a
  Claude session: `Artifact` `read` the artifact URL first (a publish to a URL the
  session has not read is refused), merge any change made there into the file
  here, then `publish` this file with `url` set to that URL and no `icon`. The
  page carries a wrapper line the publisher added; keep it.
- Write for the guide's reader: lay terms, and no file paths in the product and
  voice guides.
