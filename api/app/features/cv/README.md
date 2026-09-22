# cv

## Purpose

A learner's curriculum vitae, read into sections.

The retiring consumer backend had this for one exam's portfolio screen: upload
a PDF, pull the text, ask a model to split it into experience, education,
publications and the rest, and show the result back. It ran the model on a
thread pool inside the web process and kept the outcome in a Firestore document.
Here it is one slice, exam-agnostic — a CV belongs to a person, not to a product
— with the model call moved to a background job and the outcome in Postgres.

## Aggregates & invariants

`Cv` is the aggregate: one row per upload, owned by one user.

- **The row is written before the model is called.** An upload creates a
  `processing` row and enqueues the read in the same transaction (ADR 0006), so
  a person who closes the tab comes back to a result rather than to nothing, and
  a row is never left waiting for a job that rolled back.
- **`status` moves one way**: `processing` → `completed` or `failed`. The job
  that finds a row no longer `processing` does nothing, so a redelivery cannot
  overwrite a finished read.
- **The PDF is not kept.** Its text is pulled on upload and stored; the
  structured sections are what the product shows. The retiring backend kept
  neither the bytes nor a re-parseable file, and nothing here needs to.
- **A CV is yours or it is nobody's.** Reading another person's id answers
  `cv_not_found`, not `forbidden`, so an id cannot be probed to learn whose it
  is. The list is filtered by the token's user and never takes a user id.
- **Cheap checks run first.** Type, size and "did this PDF hold any text" are
  domain rules refused before any model is paid to read a scan or a wrong file.

## Routes

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/cv` | bearer | multipart `file`; 201 with a `processing` row. `invalid_cv_file` (422), `too_many_requests` (429) |
| GET | `/api/v1/cv` | bearer | your own, most recent first, capped |
| GET | `/api/v1/cv/{cv_id}` | bearer | `cv_not_found` (404) if it is not yours |

## Jobs

`extract_cv` (queue `cv`) reads one CV's stored text into `StructuredCv` with a
model and records the outcome on the row. Enqueued by `upload` in its own
transaction. A failure — no API key, a model error, an empty parse — is written
to the row's `error` and its `status` set to `failed`, so the person sees why
rather than watching `processing` forever.

## Cross-slice dependencies

None. The owner is the token's user; this slice never reads `identity`'s table
and resolves no exam, so it sits above nothing and calls nothing back.
