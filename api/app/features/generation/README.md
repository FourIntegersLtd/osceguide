# generation

## Purpose
Drafting content with a language model, for the platform staff who author it:
a station from a prompt, an A-to-Z summary, a blog post, a slide deck. What
comes back is a draft for a person to edit and publish through `stations` or
`media`; nothing here writes a row.

Ports the four `autogenerate_*` routes of the legacy b2c admin console
(`platform-web/docs/BACKLOG.md` M-2), behind `PlatformAdmin` rather than an email list.

## Aggregates & invariants
None. This slice owns no tables and stores nothing: a generated draft exists
only in the response, and becomes content when an author saves it elsewhere.

- Every route is `PlatformAdmin`. Generation costs money and its output is
  published under the platform's name.
- Refuses with `generation_unavailable` when no model key is configured, so a
  deployment without one fails loudly rather than answering an empty draft.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/platform/generate/station` | platform admin | `{prompt, exam_code}` → a station draft |
| POST | `/api/v1/platform/generate/summary` | platform admin | `{prompt, exam_code?}` → an A-to-Z summary draft |
| POST | `/api/v1/platform/generate/blog` | platform admin | `{prompt, exam_code?}` → a blog draft |
| POST | `/api/v1/platform/generate/slide-deck` | platform admin | `{prompt, exam_code?}` → a slide deck draft |

## Jobs
None. Generation runs inside the request; a draft is not owed to anybody if
the request fails.

## Cross-slice dependencies
None. Reads `core.settings` for the model key.
