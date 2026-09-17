# Glossary

Read this before the schema. Most of these terms come from UK postgraduate medical
examining rather than from software, they are used precisely, and several look like
synonyms while naming different things — a **cohort** is not a **trainee group**, a
**slot** is not an **attempt**, and an **entitlement** is not a **payment**.

Maintained alongside `DATA-MODEL.md`. Published version:
https://claude.ai/artifact/DdGp1umMckFMvBiiMaLPWQ

## Exams

Each is a row in `exams`, not a code branch. A fifth exam is a row — and not
necessarily ours: an exam has an **owner** (ADR 0017). The four below are the
*platform* exams, the consumer catalogue. An institution writes its own
alongside them, which the platform never sees.

| Term | Meaning |
|---|---|
| OSCE | Objective Structured Clinical Examination — the format they share: a candidate rotates through timed stations, each a scripted clinical encounter, marked against a rubric. |
| exam owner | `platform` or `org`. A platform exam is the consumer catalogue; an org exam is one institution's own, published on its own schedule and invisible outside it. A code is unique per owner, so two schools may both have a `finals`. |
| programme | One organisation offering one exam — its own or a platform one. Carries no content: it is the label a year's sittings are grouped under. Its status (`draft`/`active`/`retired`) is the institution's and is separate from the exam's (`draft`/`published`/`retired`), which is the owner's. |
| SCA (`sca`) | RCGP Simulated Consultation Assessment. UK GP licensing. 3 min reading, 15 min simulation — the longest of the four. |
| PLAB 2 (`plab`) | GMC PLAB Part 2, for internationally qualified doctors seeking UK registration. 90 s reading, 10 min simulation. |
| CASC (`casc`) | RCPsych Clinical Assessment of Skills and Competencies — psychiatry. Same timings as PLAB. |
| ortho (`ortho`) | FRCS Trauma & Orthopaedics. 2 min reading, 11 min simulation, and the only exam with four distinct station subtypes. |
| framework_id | What a result is recorded under: the id of the **rubric version** the exam names, so a stored result traces back to the exact wording it was marked against. Was a string column naming one of four frameworks the engine shipped (ADR 0016). |

## Content

| Term | Meaning |
|---|---|
| station | One clinical scenario a candidate can be given. Owned by the platform library (`owner_kind = 'platform'`) or an institution (`'org'`). A container; content lives in versions. |
| station version | One immutable revision of a station's content. **This is what everything points at** — attempts, slots, circuit stations and set entries hold a `station_version_id`, never a `station_id`. |
| station template | A reusable authoring skeleton an org defines, itself versioned. |
| station schema | An org's field definition: what a station of a given kind contains. Authored per organisation, so no fixed columns, so JSON. |
| feedback template (rubric) | An institution's narrowing of the platform marking schema. Versioned; a sitting cannot be created without a **published** version bound to it. |
| field selection | The body of a feedback template version: paths into the exam's JSON Schema. A selection over a document, which is why it is JSON. |
| media item | A slide deck, summary, blog post or podcast — one table with a `kind`, replacing sixteen legacy collections. |

## Doing an assessment

| Term | Meaning |
|---|---|
| attempt | **One candidate running one scenario, once.** The central record; transcript and marking hang off it. Its id is its own — not the room name, not the slot id. |
| attempt kind | Six, and the kind determines the single reference it may carry: `practice` / `self_practice` (none), `set_station` (set entry), `debrief` (source attempt), `exam_slot` (slot), `peer` (practice session). Enforced by CHECK. |
| definition | The frozen, fully rendered prompt document handed to the worker. Written once, on the first **successful** render; a degraded render is served but not persisted. The worker holds no templates. |
| debrief | A second conversation *about* a finished attempt rather than a fresh sitting. |
| transcript | Two tables: `transcript_messages` holds turns, `transcripts` is the delivery record. |
| assessment result | What the engine scored, unique per `(attempt, policy_version)`. |
| policy version | Which marking policy produced a result. A change produces a new row, never an update. |
| the engine (`osce_assessment`) | The separate package that renders prompts and scores transcripts. Knows nothing about HTTP, orgs or users. |

## Institutions running exams

There is no separate employer product — an exam is a **mode** on a sitting.

| Term | Meaning |
|---|---|
| sitting | One scheduled examining event. Carries the bound rubric and the mode. |
| mode | `training` or `exam`. The exam arm of the business is this column, not a separate product or deployment. |
| circuit | One run of stations inside a sitting: candidates rotating through stations, one supervisor, one room. |
| slot | **One trainee at one station.** Sat once. Carries no transcript and no feedback — those live on the attempt, which is what lets a re-dispatch keep the first recording. |
| supervisor | The staff member running a circuit live. An ordinary org member, not an admin. |
| dispatch | Sending the AI patient into the room. Each dispatch clears stale agents and creates a **new** attempt. |
| switch turn | Advancing to the next slot, under a row lock. |
| edit lock | Whether a circuit's structure may still be changed, and why not. |
| append trainees | Adding latecomers into a circuit already running. |
| station set | A learner's **own** collection of stations, with attempt counters. The counters are why a set is not a circuit: a set entry can be re-run, a slot cannot. |

## People and access

Four different nouns for a person, each meaning something different.

| Term | Meaning |
|---|---|
| user | One human, one row, one email. |
| principal | The decoded access token in a request. Not a table. |
| membership | A person's role in one organisation. A user may hold several, in several orgs. |
| workspace | The org context a request acts in, resolved from `{org_slug}`. |
| trainee | Someone an institution teaches. **Distinct from a user**: institutions roster people by email long before they sign in; `user_id` fills in when they do. |
| cohort | An intake — the year group. One per trainee. |
| trainee group | An arbitrary group for addressing and practice. **Not a cohort**: several per trainee, real rows, normalised label. |
| GP Lead | A senior reviewer giving a revisioned second opinion. Here they are an institution admin — no separate role or product. |
| platform admin | A column on `users`, not a role or an email allowlist. |
| entitlement | **May this person attempt this exam now, and why.** Separate from whatever caused it. |
| source | What caused an entitlement: `purchase`, `org_grant`, `trial`, `sso_tenant`, `admin`. |

## Marking and outcomes

| Term | Meaning |
|---|---|
| slot review | A rubric filled against one slot, by staff or a peer observer. One per person per slot. |
| GP Lead review | The revisioned second opinion. One per slot, edited in place, revision counter for concurrent editors. |
| circuit review | What a supervisor finalises across a whole circuit. |
| RAG | Red / Amber / Green, the UK clinical assessment severity scale. Single character; red is worst. Aggregation is meant to move server-side and has not. |
| candidate result | An institution's **formal** outcome. Append-only, enforced by trigger: a change is a new revision. |
| workflow state | `draft` → `signed_off` → `released`. Signed-off names its signer, released names its releaser. |
| assessment outcome | `pass`, `fail`, `inconclusive`, `withheld`. |
| recruitment outcome | `hired`, `reserve`, `not_hired`, `withdrawn`, `pending`. A separate axis, cross-checked for compatibility. |
| evidence fingerprint | A hash of what a decision was made against, so a result signed off on one set of scores cannot be released after they move. |
| release | Making a result visible to the candidate. Before release, `GET /me/results/{sitting_id}` shows nothing. |

## Practising with other people

Two mechanisms that are easy to confuse.

| Term | Meaning |
|---|---|
| marketplace | **Scheduled** peer practice: someone posts a free time, someone claims it, a peer session is created. |
| peer practice | **Automatic** matching: join a queue, get paired. Ordered by an identity sequence, not `created_at`. |
| doctor / patient | The two parts in a peer session. `practice_history` remembers which you last played. |
| audience / visibility | Who social content is addressed to: `public`, one `organisation`, or one `group`. Deliberately opaque — nothing in the mechanism knows what a group *is*. |

## Voice

| Term | Meaning |
|---|---|
| LiveKit | The realtime audio platform. **The SFU is always Cloud**; only agent workers are self-hosted. |
| worker | The agent process that plays the simulated patient or assistant. Lives in `assessment-platform`, authenticates with a shared secret, holds no templates. |
| room | A LiveKit room, named independently of the attempt id. |
| family | Which worker a session needs: `assessment` (conversation, admin-test, debrief) or `assistant` (help, onboarding, dashboard, consulting-doctor). |
| routing mode | `self-hosted` or `livekit-cloud`. |
| cloud slot | A counted reservation against the Cloud concurrency cap, held in Redis. |
| assistant | The non-assessment agent. Transcripts kept only for `help`. |

## How the code is organised

| Term | Meaning |
|---|---|
| slice | A vertical module under `app/features/` owning its tables, domain, repository, service and router. 22 of them. A slice may call another slice's **service** — never its repository, models or domain. |
| domain | `domain.py`: plain Python invariants. No SQL, no FastAPI, no I/O — enforced by a guard. |
| repository | The only place SQL lives. Mapped classes never leave it. Org-scoped methods take `org_id` first. |
| service | The use cases. Raises typed `AppError`s and **never commits**. |
| router | Parse, call one service function, return a schema. |
| port | A Protocol in `core/ports.py` for anything external, with a fake beside it. |
| guard | An architecture test under `tests/guards/` that scans the AST. Each ships a meta-test that plants a violation. |
| oracle | A legacy test ported onto the new routes — the evidence behaviour survived. |
| golden test | A captured output that must be reproduced byte-for-byte. |
| error code | `ErrorResponse.code`. The frontend switches on this, never on `message`, so renaming one is a breaking change. |
| Page / cursor | Every list route returns `Page[T]` with a cursor. |

## Words the build will reject

`tests/guards/test_no_legacy_vocabulary.py` scans every file in `app/` and fails the
build on these nine tokens. It is a backstop, not documentation — which is why they
are listed here.

```
app_type · apptype · collection_mapping · firestore
admin_user_emails · local_store · localstore · b2c · b2b
```

**The replacements.** Exams are rows in the `exams` table, not an `app_type` string
keying four collections per entity. Products are memberships and entitlements, not a
`b2b`/`b2c` branch. Admins are a column on `users`, not a list of emails in a
constant. Persistence is Postgres through a repository — there is no local store and
no Firestore.

**Matching is by substring, not whole word.** `offenders()` in `tests/guards/_scan.py`
does `if banned in token` over every identifier *and every runtime string literal*, so
`b2b` fires on `b2b_exams`, on `legacy_b2b_id`, and on any string containing it.

**Docstrings are exempt, deliberately.** Prose explaining what a module replaces
carries no penalty; identifiers and runtime string literals do.

**There is exactly one quarantine: `app/migration/`.** It must read the old shapes to
translate them. Nothing outside it may import it. This has a live consequence:
attempts record their origin as `legacy_ref` values like `b2c:transcript:abc123`, so
**any code that builds or parses that prefix must live inside `app/migration`**, or it
trips the guard by construction. The package is deleted once every tenant is across.

**Four terms have no stated replacement** — `firestore`, `collection_mapping`,
`local_store`, `localstore`. If you trip one, the failure tells you to stop but not
where to go. Ask, then add the answer here.
