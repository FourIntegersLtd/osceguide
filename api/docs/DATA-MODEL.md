# The data model, field by field

> ## This document is load-bearing. Keep it current.
>
> The backend is still being rebuilt. Every slice that lands, every column added
> or dropped, every constraint tightened, changes what is true here — and a
> schema reference that is 80% right is worse than none, because people stop
> checking it against the code and start trusting it.
>
> **The rule: a migration and this document change in the same commit.** The same
> rule `CONTRIBUTING.md` already applies to tests — no behaviour change without a
> test beside it — applies to the schema. If `make new-migration` produced a diff,
> this file is part of that diff. A PR that adds a table and not its section here
> is incomplete in the same way a PR with no test is incomplete.
>
> **It is no longer a promise.** `scripts/check_data_model.py` imports
> `Base.metadata`, diffs the table and column names against the headings and
> field rows below, and fails on anything present in one and absent from the
> other. It runs in `make arch`, so it runs in `make ci`. Run it on its own with
> `make data-model`.
>
> It is tolerant about form and strict about presence: a column counts as
> documented when its name appears inside any backticked span of its table's
> section, so a field row, a pair on one row, a sentence for a join table and
> the `published_at/by` shorthand all satisfy it. A column mentioned nowhere
> does not.
>
> **What must stay true, not just present.** Column names and types are the easy
> half and the half a checker can hold. The half that rots silently is the
> *reasoning* — why a delete rule is `RESTRICT`, why a unique index is partial,
> why a column is JSON. When a constraint changes, change the sentence that
> explains it, or the next engineer will implement against a rationale that no
> longer holds.
>
> Last verified against the code: **2026-09-18**, branch `feat/tutor-memory`.
> `scripts/check_data_model.py` runs on every `make arch`, so the table and
> column names here cannot drift from the schema; what no checker holds is the
> *reasoning*, which is most of what this document is for.
> There is also a published version of this reference, kept in step with it:
> https://claude.ai/artifact/DdGp1umMckFMvBiiMaLPWQ


70 tables across 24 slices. Every table's classes live in `app/features/<slice>/models.py`
and never leave that slice's repository.

## Conventions

Three things are true of almost every table, so they are not repeated below:

| | |
|---|---|
| `id` | `uuid`, primary key, generated in Python (`uuid.uuid4`), from the `UUIDPrimaryKey` mixin |
| `created_at`, `updated_at` | `timestamptz not null default now()`, `updated_at` bumped on write, from the `Timestamps` mixin |
| Constraint names | fixed by a naming convention on `Base.metadata` (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`), so Alembic can drop them by name later |

Tables that deliberately have **no `updated_at`** are called out: `audit_log`, `user_mfa`, `user_mfa_recovery_codes`,
`transcript_messages`, `assistant_transcript_messages`, `circuit_stations`,
`circuit_trainees`, `candidate_result_revisions`, `candidate_result_events`,
`stripe_events`. Nothing edits those rows; a change is a new row.

`citext` is used for anything a human types and expects to match case-insensitively:
emails, org slugs, exam codes.

### The `Addressed` mixin

Three tables — `posts`, `availability_posts`, `practice_queue_entries` — carry who a
row is addressed to, as a mixin rather than three copies, because the constraint is
what stops a row claiming to be private while naming nobody:

| Field | Type | Notes |
|---|---|---|
| `visibility` | `varchar(16) not null default 'public'` | `public` \| `organisation` \| `group` |
| `audience_org_id` | `uuid null` → `organizations.id` ON DELETE CASCADE | |
| `audience_group_id` | `uuid null` → `trainee_groups.id` ON DELETE CASCADE | |

CHECK `AUDIENCE_CHECK`: public names neither, organisation names an org only, group
names both.

---

# Foundation

## identity — 5 tables

### `users`
| Field | Type | Notes |
|---|---|---|
| `email` | `citext not null unique` | citext so `Alice@…` and `alice@…` collide in the database, not only in code that remembers to lowercase |
| `name` | `varchar(200) not null default ''` | |
| `password_hash` | `text null` | null for provider-only accounts |
| `status` | `varchar(32) not null default 'active'` | |
| `is_platform_admin` | `bool not null default false` | |
| `must_change_password` | `bool not null default false` | gates all but `ROUTES_ALLOWED_WHILE_PASSWORD_EXPIRED` |
| `password_login_disabled` | `bool not null default false` | set once by `identity.service_sso.sign_in_external` when this person signs in through an `sso_only` organisation; `identity` sits below `sso` and cannot read that configuration at login time, so the fact is written down here instead. Never cleared automatically |
| `last_login_at` | `timestamptz null` | |
| `closed_at` | `timestamptz null` | set by `identity.service_close_account.close_account`; the scheduled erasure job (`identity/jobs.py`) reads it to find every account closed more than 30 days ago |
| `erased_at` | `timestamptz null` | set by `identity.service_erasure.erase_account` once the account's personal fields and content are scrubbed; also the job's idempotency check |
| `exam_date` | `date null` | when they sit the real thing; the consumer dashboard counts down to it |
| `exam_time` | `time null` | the time of day on `exam_date`, optional; cleared whenever `exam_date` is cleared, since a time with no date names nothing |
| `exam_code` | `varchar(32) null` | which exam they signed up for; a preference, not a grant |
| `extra_reading_percent` | `int not null default 0` | superseded on the live API surface by `needs_extra_time`/`custom_reading_seconds`/`custom_simulation_seconds` below (A3); the column and its CHECK 0–100 stay only for `app.migration`, which still derives it from the same legacy flag |
| `needs_extra_time` | `bool not null default false` | the access-arrangement gate: the two custom timers below apply only while this is set (legacy `Timer.tsx`/`MockRule.tsx` kept the durations even when the checkbox was off) |
| `custom_reading_seconds` | `int null` | a reading-timer override in seconds. CHECK 1–3659 (60 minutes 59 seconds, the legacy modal's ceiling) when not null |
| `custom_simulation_seconds` | `int null` | a simulation-timer override in seconds. Same CHECK 1–3659 when not null |
| `ai_training_consent` | `bool not null default false` | whether this person's consultations may be used to train models |
| `colleague_waiting_email` | `bool not null default false` | email when a peer is waiting to practise |
| `replay_onboarding` | `bool not null default false` | offer the guided voice tour again on the dashboard |
| `consumer_role` | `varchar(32) not null default 'user'` | staff vs learner on the consumer product |
| `avatar_url` | `text null` | this person's profile photo, written by `identity.service.upload_avatar`; stored in S3 like a station photo |

Domain: `MIN_PASSWORD_LENGTH = 12`.

### `user_identities`
An external provider's handle on a user: Clerk today, others later. **Written by
nothing yet** — the repository functions exist and have no callers, because no
SSO flow has been built. See `organization_sso` below.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | |
| `provider` | `varchar(32) not null` | |
| `subject` | `varchar(255) not null` | the provider's own id |
| `tenant_slug` | `varchar(100) null` | for provider-side tenancy |

UNIQUE `(provider, subject)`.

### `organization_sso`
One organisation's sign-in arrangement. At most one row per organisation.

Replaces a hostname allow-list that was compiled into the browser bundle, with
the tenant slug, the button's wording and the "no password form here" rule
beside it.

| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid not null` → `organizations.id` CASCADE | UNIQUE |
| `provider` | `varchar(32) not null` | `clerk` or `entra`; selects which adapter verifies the id token at sign-in |
| `issuer` | `varchar(255) null` | the broker's own identity. Not a secret |
| `enabled` | `bool not null default false` | |
| `sso_only` | `bool not null default false` | refuses password sign-in for the org when set. CHECK `NOT sso_only OR enabled` — otherwise one checkbox leaves nobody a way in |
| `sign_in_label` | `varchar(80) null` | null takes the provider's default rather than rendering a button with no words |
| `default_exam_code` | `varchar(32) null` | which exam a white-label site lands on |

Sign-in exchanges the broker's code for an id token, then verifies issuer,
audience and signature against the provider's JWKS (`sso/entra.py` for Entra,
`sso/clerk.py` for Clerk). When `sso_only` is true, password login is refused
for that organisation (`identity/service_sessions.py`, `login_with_memberships`,
enforced in the database by migration
`02a17a847052_sso_only_disables_password_login`).

### `organization_sso_bindings`
A host, or an email domain, that means one organisation.

| Field | Type | Notes |
|---|---|---|
| `sso_id` | `uuid not null` → `organization_sso.id` CASCADE | |
| `kind` | `varchar(16) not null` | CHECK `host` or `email_domain` |
| `value` | `citext not null` | stored as a `Host:` header will arrive: lower-cased, no scheme, path or port |

UNIQUE `(kind, value)` — across the whole platform, not within an organisation.
A hostname belongs to exactly one, and two rows claiming `nhs.net` would make
home-realm discovery a coin toss.

### `cvs`
A learner's uploaded CV, and what was read out of it. The PDF is not stored:
its text is pulled on upload and the structured result is what the product
reads back. `created_at` is the upload time the list sorts by.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | indexed; a CV is read by its owner and nobody else |
| `status` | `varchar(16) not null default 'processing'` | moves one way: `processing` → `completed` or `failed` |
| `original_filename` | `varchar(255) not null default ''` | what the person called the file; never re-opened |
| `extracted_text` | `text null` | the PDF's text, so the job needs neither the file nor a second parse |
| `structured` | `jsonb null` | the sections, as `cv.schemas.StructuredCv`. Null until the job completes |
| `error` | `text null` | why it failed, for the person to read. Null unless `status` is `failed` |
| `completed_at` | `timestamptz null` | when the read finished |

### `site_messages`
Somebody wrote to us from the public site, or from inside the product.

| Field | Type | Notes |
|---|---|---|
| `kind` | `varchar(32) not null` | CHECK `contact` or `product_feedback`. Separate because they are read by different people |
| `name` | `varchar(120) null` | |
| `email` | `citext null` | required for `contact` (in the domain, not the column): somebody asking a question has to be answerable |
| `subject` | `varchar(200) null` | |
| `body` | `text not null` | |
| `user_id` | `uuid null` → `users.id` SET NULL | set when the sender was signed in; null says nothing about whether they have an account |
| `source` | `varchar(200) null` | which screen the feedback is about |
| `handled_at` | `timestamptz null` | |
| `handled_by` | `uuid null` → `users.id` SET NULL | |

INDEX `(kind, created_at)` — the inbox reads one kind at a time, newest first.

### `refresh_chains`
One sign-in, from which a series of refresh tokens is issued.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | |
| `expires_at` | `timestamptz not null` | |
| `revoked_at` | `timestamptz null` | |
| `revoked_reason` | `varchar(32) null` | |
| `user_agent` | `varchar(255) null` | |

### `refresh_tokens`
| Field | Type | Notes |
|---|---|---|
| `chain_id` | `uuid not null` → `refresh_chains.id` CASCADE | indexed |
| `token_hash` | `varchar(64) not null unique` | |
| `used_at` | `timestamptz null` | |

Every token is kept, spent or not, because that is the only way reuse can be told
from forgery. Overwriting a single `current_token_hash` on rotation loses the
evidence: a replayed token is simply not found, which is indistinguishable from a
token that never existed, so the leaked chain stays alive.

### `password_reset_tokens`
`user_id` → `users.id` CASCADE, `token_hash varchar(64) not null unique`,
`expires_at timestamptz not null`, `used_at timestamptz null`.

### `user_mfa`
One authenticator for one account. `user_id` is the primary key, so there is
no second secret. `confirmed_at` stays null until a code from that secret has
been accepted; until then the row is an enrolment in progress, not a second
factor. `last_used_step` is the TOTP counter of the last accepted code, and a
later code at that step or earlier is refused as a replay. The secret is
Fernet ciphertext under `MFA_SECRET_KEY`, never the shared secret itself.
No `updated_at`.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | primary key |
| `secret_ciphertext` | `text not null` | Fernet token, not the TOTP secret |
| `confirmed_at` | `timestamptz null` | null until the first code is accepted |
| `last_used_step` | `bigint null` | replay window; a step at or below this is refused |
| `created_at` | `timestamptz not null default now()` | |

Password login, registration and the legacy token exchange all go through
one gate (`identity.service_mfa.finish_password_sign_in`). When the
authenticator is confirmed the response is `mfa_required` and a challenge
JWT (`typ` `mfa_challenge`, five minutes). When policy requires one and none
is confirmed, the response is `mfa_enrolment_required` (`typ` `mfa_enrol`,
ten minutes). The access-token verifier rejects both types.

SSO sign-in (`identity.service_sso.sign_in_external`) does not use the gate.
The identity provider owns the second factor, so this platform does not ask
for another. Password reset and accepting an invitation do not mint a
session; they set a password, and the next login is the gate.

Requiring MFA, or an organisation turning `require_staff_mfa` on, takes
effect at the next password sign-in. A refresh chain already issued keeps
working until it expires or is revoked.

### `user_mfa_recovery_codes`
Ten single-use codes, shown once when the authenticator is confirmed or when
they are regenerated. Only the argon2 hash is stored. No `created_at` or
`updated_at`: `used_at` is the only clock that matters.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | indexed |
| `code_hash` | `text not null` | argon2id, same hasher as a password |
| `used_at` | `timestamptz null` | set when the code signs someone in; a second use is refused |

## tenancy — 3 tables

### `organizations`
| Field | Type | Notes |
|---|---|---|
| `slug` | `citext not null unique` | the URL identifier and nothing else — every FK everywhere points at `id`, which is the mistake b2b made the other way round |
| `name` | `varchar(200) not null` | |
| `org_type` | `varchar(32) not null default 'institution'` | |
| `status` | `varchar(32) not null default 'trial'` | `ACTIVE_ORG_STATUSES = {trial, active}`; suspension writes `suspended` |
| `parent_org_id` | `uuid null` → `organizations.id` SET NULL | self-reference, for partner hierarchies |
| `contract_starts_at` / `contract_ends_at` | `timestamptz null` | |
| `suspended_at` | `timestamptz null` | |
| `suspended_by` | `uuid null` → `users.id` SET NULL | |
| `require_staff_mfa` | `bool not null default false` | when set, a membership whose role is outside `END_USER_ROLES` must use a second factor. Same precedent as `organization_sso.sso_only`: the organisation states a sign-in rule. Takes effect at the next password sign-in; existing refresh chains continue |

### `memberships`
A person's role in an organisation. A user may hold several, in several orgs.

| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid not null` → `organizations.id` CASCADE | |
| `user_id` | `uuid not null` → `users.id` CASCADE | indexed |
| `role` | `varchar(32) not null` | see role sets below |
| `product_surface` | `varchar(32) null` | which surface this membership is for |
| `status` | `varchar(32) not null default 'active'` | revoking writes `revoked` |
| `revoked_at` | `timestamptz null` | |

UNIQUE `(org_id, user_id, role)`.

Role vocabularies live in `tenancy.domain`:
`ORG_ADMIN_ROLES = {owner, admin, institution_admin, partner_admin}`,
`INSTITUTION_ADMIN_ROLES = {owner, admin, institution_admin}`,
`END_USER_ROLES = {trainee, practice_user}`, `ASSIGNED_STAFF_ROLE = "supervisor"`.

### `audit_log`
Append-only. No `updated_at`: nothing edits these.

| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid null` → `organizations.id` CASCADE | |
| `actor_user_id` | `uuid null` → `users.id` SET NULL | |
| `actor_email` | `varchar(320) null` | kept even when the user row goes |
| `action` | `varchar(100) not null` | |
| `target_type` | `varchar(64) null` | |
| `target_id` | `varchar(200) null` | text, because targets are of every type |
| `summary` | `text null` | |
| `meta` | `jsonb null` | mapped from the column `metadata` |
| `at` | `timestamptz not null default now()` | |

Indexes on `(org_id, at)` and `(actor_user_id, at)`.

## catalog — 2 tables

### `exams`
**Starts empty.** An exam is written, not seeded — by a platform admin through
`POST /platform/exams`, or by an institution through `POST /orgs/{slug}/exams`.
Replaces b2c's `app_type` string and the 4×20 `COLLECTION_MAPPING` it indexed —
a fifth exam is a row here, not another twenty collection names, and not a
release either: four rows used to be inserted by a migration and mirrored by a
frozen tuple in `catalog.domain`, pinned to each other by a unit test.

**Owned** (ADR 0017), the same way a station or a rubric is. A *platform* exam is
the consumer catalogue. An *org* exam is an institution's own: written without
asking us, published on its own schedule, and never in `GET /exams`.

| Field | Type | Notes |
|---|---|---|
| `owner_kind` | `varchar(16) not null default 'platform'` | `platform` (the consumer catalogue) or `org` |
| `org_id` | `uuid null` → `organizations.id` CASCADE | set iff `owner_kind = 'org'` |
| `code` | `citext not null` | lower-case, URL-safe; appears in plans and partner ref ids, so it is never renamed. Unique **per owner**, not globally |
| `name` | `varchar(200) not null` | |
| `status` | `varchar(32) not null default 'draft'` | `draft` → `published` → `retired`, per owner; only a published exam may be built on |
| `rubric_version_id` | `uuid null` → `rubric_versions.id` RESTRICT | what it is marked against. A platform exam's must be published and platform-owned; an org exam's may be its own or a platform one |
| `default_reading_seconds` | `int not null` | |
| `default_simulation_seconds` | `int not null` | |
| `station_attempt_limit` | `int not null default 3` | |
| `partner_pilot` | `bool not null default false` | whether a partner attribution link may name it; was `growth.domain.PILOT_EXAMS`. Consumer-side, so forced false on an org exam |

CHECK `ck_exams_published_has_rubric`: `status <> 'published' OR rubric_version_id IS NOT NULL`
— an exam that could be sat and then found unmarkable is the failure this prevents.

CHECK `ck_exams_owner_matches_org`: `owner_kind = 'platform'` requires `org_id IS NULL`,
`owner_kind = 'org'` requires it set.

UNIQUE `uq_exams_platform_code` on `(code) WHERE org_id IS NULL` and
`uq_exams_org_code` on `(org_id, code) WHERE org_id IS NOT NULL`. One namespace
would let whoever registered a code first reserve it for every institution.

`framework_id` is gone. What everything downstream records is the rubric
version's own id, so a stored result traces back to the exact wording it was
marked against; the column named one of four frameworks the engine shipped.

### `org_programmes`
One organisation offering one exam. This is what `b2b_exams` rows were. The exam
is either the institution's own or one the platform published; the programme
carries no content, it is the label a year's sittings are grouped under.

| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid not null` → `organizations.id` CASCADE | |
| `exam_id` | `uuid not null` → `exams.id` RESTRICT | an exam this org can see |
| `status` | `varchar(32) not null default 'draft'` | `OFFERABLE_PROGRAMME_STATUSES = {active}`. The institution's own status, separate from the exam's |
| `source` | `varchar(32) not null default 'custom'` | `imported_osce_guide` when adopted through `POST /orgs/{slug}/exams/import` |
| `import_ref` | `jsonb null` | where an imported programme came from |

UNIQUE `(org_id, exam_id)`.

---

# Content

## rubrics — 2 tables

What a candidate is marked against, and who wrote it. This used to be three
files in the engine package — a Python constant, a hand-written JSON Schema
whose `description` strings were the only place the marking descriptors
existed, and one of three `.txt` prompts chosen by a dict keyed on framework
id — so adding an exam meant a release of the engine.

### `rubrics`
Owned by the platform or by one organisation, the same shape `stations` uses.
Deliberately has **no `exam_id`**: an exam names the rubric version it is marked
with, never the other way round, which is what lets an institution author a
rubric without first inventing an exam to hang it on.

| Field | Type | Notes |
|---|---|---|
| `owner_kind` | `varchar(16) not null` | `platform` or `org` |
| `org_id` | `uuid null` → `organizations.id` CASCADE | null exactly when `owner_kind='platform'` |
| `title` | `varchar(200) not null` | |
| `current_version_id` | `uuid null` → `rubric_versions.id` SET NULL | set on publish |

CHECK `ck_rubrics_owner_matches_org`: `(owner_kind='platform' AND org_id IS NULL) OR (owner_kind='org' AND org_id IS NOT NULL)`.

### `rubric_versions`
One immutable revision. The version's **id is the framework id** the engine and
`attempt_results.framework_id` record, so a result traces back to the exact
wording of the rubric that produced it.

| Field | Type | Notes |
|---|---|---|
| `rubric_id` | `uuid not null` → `rubrics.id` CASCADE | |
| `org_id` | `uuid null` → `organizations.id` CASCADE | mirrors the rubric's owner |
| `version` | `int not null` | UNIQUE `(rubric_id, version)` |
| `structure` | `jsonb not null` | scale, domains, competencies and their descriptors — authored, so it has no fixed columns |
| `system_prompt` | `text not null` | the marking instructions; was a `.txt` file in the engine |
| `pacing` | `jsonb not null` | the consultation clock: four marks in seconds |
| `result_schema_override` | `jsonb null` | escape hatch for a shape the derivation cannot express; normally null |
| `marking_layout` | `jsonb null` | examiner / structured human review UI (`StationStructure`); required on publish for platform catalogue rubrics |
| `status` | `varchar(32) not null default 'draft'` | `draft` → `published` → `archived` |
| `published_at/by` | `timestamptz null`, `uuid null` → `users.id` SET NULL | |
| `archived_at/by` | `timestamptz null`, `uuid null` → `users.id` SET NULL | |

The result schema a marker fills is **derived** from `structure`, not stored:
the descriptors an author typed become the property descriptions the model
reads, so the two cannot drift apart.

---

## stations — 4 tables

### `station_templates`
A station shape: what a station of this kind contains, and what each block of
it is for. Owned by the platform or by an org — it was org-only, so the
platform's library stations had no template and were rendered by a formatter
that branched on the exam's code, which is why a new exam needed engine code.

| Field | Type | Notes |
|---|---|---|
| `owner_kind` | `varchar(16) not null` | `platform` or `org` |
| `org_id` | `uuid null` → `organizations.id` CASCADE | null exactly when `owner_kind='platform'` |
| `exam_id` | `uuid null` → `exams.id` SET NULL | a label, not a binding |
| `title` | `varchar(200) not null` | |

CHECK `ck_station_templates_owner_matches_org`.

(`station_schemas` is gone. It was a second document-shaped table for the same
idea — "what a station of this kind contains" — with no repository, service,
route or reader anywhere in the app or the tests.)

### `station_template_versions`
| Field | Type | Notes |
|---|---|---|
| `owner_kind` | `varchar(16) not null` | mirrors the template's owner |
| `org_id` | `uuid null` → `organizations.id` CASCADE | |
| `template_id` | `uuid not null` → `station_templates.id` CASCADE | |
| `version` | `int not null` | |
| `structure` | `jsonb not null` | `{"blocks": [{id, label, kind, required, role}], "layout": {greeting, persona}}`. The `role` on each block is what the renderer places it by — the reason one formatter now serves every station |
| `status` | `varchar(32) not null default 'draft'` | `draft` \| `published` \| `archived` |
| `published_at` / `published_by` | `timestamptz null` / `uuid null` → `users.id` SET NULL | |
| `archived_at` / `archived_by` | same shape | |

UNIQUE `(template_id, version)`; index `(org_id, status)`; CHECK `ck_station_template_versions_owner_matches_org`.

### `stations`
A scenario a candidate can be given. `owner_kind` is what unifies b2c's four
Firestore collections with b2b's org-authored instances: the platform library and an
institution's own stations are the same thing with a different owner, so an attempt
points at one column rather than a union of sources.

| Field | Type | Notes |
|---|---|---|
| `owner_kind` | `varchar(16) not null` | `platform` \| `org` |
| `org_id` | `uuid null` → `organizations.id` CASCADE | |
| `exam_id` | `uuid not null` → `exams.id` RESTRICT | |
| `title` | `varchar(300) not null` | |
| `status` | `varchar(32) not null default 'draft'` | `draft` \| `published` \| `archived` |
| `current_version_id` | `uuid null` → `station_versions.id` SET NULL (`use_alter`) | set once a version is published; attempts bind to the version, never here |

CHECK `ck_stations_owner_matches_org`: `platform` ⇒ `org_id IS NULL`, `org` ⇒
`org_id IS NOT NULL`. Indexes `(org_id, exam_id)` and `(exam_id, owner_kind)`.

### `station_versions`
One immutable revision of a station's content. An attempt references a version, never
a station, so editing a station tomorrow cannot change what somebody was assessed on
yesterday.

| Field | Type | Notes |
|---|---|---|
| `station_id` | `uuid not null` → `stations.id` CASCADE | |
| `org_id` | `uuid null` → `organizations.id` CASCADE | |
| `version` | `int not null` | |
| `content` | `jsonb not null` | the justified JSON: the four exams have genuinely different document shapes — SCA's management plan, PLAB's examination findings, ortho's four station subtypes. Schema-validated at the boundary by the engine |
| `template_version_id` | `uuid null` → `station_template_versions.id` SET NULL | |
| `status`, `published_at/by`, `archived_at/by` | as for template versions | |

UNIQUE `(station_id, version)`.

### `station_flags`
A report that a station is wrong, and what staff did about it. The retiring
client appended `{station_id, mock_id, flagged: true}` to the *user's* document
instead, so a report was visible only to the person who made it and the content
team never saw one at all.

| Field | Type | Notes |
|---|---|---|
| `station_id` | `uuid not null` → `stations.id` CASCADE | what the report is about, which is why this is a table of its own rather than a column on `users` |
| `user_id` | `uuid not null` → `users.id` CASCADE | who reported it |
| `status` | `varchar(16) not null default 'open'` | `open` \| `resolved` |
| `resolution_note` | `text null` | what staff wrote when they closed it; never shown to the reporter — a queue, not an inbox |
| `resolved_by` | `uuid null` → `users.id` SET NULL | |
| `resolved_at` | `timestamptz null` | cleared when a report is reopened, so an `open` row never answers twice |

UNIQUE `(station_id, user_id)`: a second tap on the button is the same report,
and the legacy answer to a repeat was a 400 the client surfaced as a failure.
CHECK `ck_station_flags_status`; index `(status, created_at)` — the queue is
"what is still open, oldest first".

`feedback_templates`/`feedback_template_versions` (a narrowing of a rubric)
were dropped 2026-09-24, migration `45481a44b73d`: authored but never
mounted in `main.py`, never called by any live route, service or frontend
caller, confirmed by a whole-tree grep before deletion. A sitting's rubric
comes via its programme instead — see `attempts.rubric_version_id` below.

## station_sets — 2 tables

### `station_sets`
A learner's own collection of stations to practise.

| Field | Type | Notes |
|---|---|---|
| `owner_user_id` | `uuid not null` → `users.id` CASCADE | indexed with `created_at` |
| `exam_id` | `uuid not null` → `exams.id` RESTRICT | |
| `name` | `varchar(200) not null` | |
| `locked` | `bool not null default false` | locked rather than deleted when access lapses, so the work reappears on renewal instead of vanishing |
| `completed_at` | `timestamptz null` | |

### `station_set_entries`
One station inside a set, with how often it has been run. The counters are the reason
a set is not a circuit: a slot is sat once.

| Field | Type | Notes |
|---|---|---|
| `set_id` | `uuid not null` → `station_sets.id` CASCADE | |
| `position` | `int not null` | |
| `station_version_id` | `uuid not null` → `station_versions.id` RESTRICT | |
| `attempts` | `int not null default 0` | capped by `exams.station_attempt_limit` |
| `debrief_attempts` | `int not null default 0` | |
| `last_attempt_at` | `timestamptz null` | |

UNIQUE `(set_id, position)`.

## media — 1 table

### `media_items`
A slide deck, summary, blog post or podcast episode. One table with a kind rather
than four per product: b2c has sixteen collections for these and the same
publish-and-read logic in each.

| Field | Type | Notes |
|---|---|---|
| `kind` | `varchar(32) not null` | `slide_deck` \| `summary` \| `blog` \| `podcast` |
| `slug` | `varchar(120) not null unique` | `MAX_SLUG = 80` on generation |
| `title` | `varchar(300) not null` | |
| `summary` | `text null` | |
| `content` | `jsonb not null default {}` | shape differs by kind — slides have a deck, a podcast has an audio url |
| `exam_id` | `uuid null` → `exams.id` SET NULL | indexed |
| `author_id` | `uuid null` → `users.id` SET NULL | |
| `status` | `varchar(16) not null default 'draft'` | |
| `published_at` | `timestamptz null` | indexed with `kind` |

Search caps at `MAX_QUERY = 300`, and currently returns nothing: no vector index is
wired behind it.

---

# The assessment core

## attempts — 5 tables

### `attempts`
One candidate running one scenario. `id` is its own identity: b2c made the attempt id
the room name and b2b made it the slot id; both leaked an implementation detail into
the worker contract, and b2b's meant re-dispatching a slot overwrote the first
recording.

| Field | Type | Notes |
|---|---|---|
| `kind` | `varchar(32) not null` | `practice` \| `self_practice` \| `set_station` \| `debrief` \| `exam_slot` \| `peer` |
| `user_id` | `uuid not null` → `users.id` CASCADE | indexed with `created_at` |
| `org_id` | `uuid null` → `organizations.id` CASCADE | indexed with `created_at` |
| `exam_id` | `uuid not null` → `exams.id` RESTRICT | |
| `station_version_id` | `uuid null` → `station_versions.id` RESTRICT | indexed |
| `slot_id` | `uuid null` → `slots.id` **RESTRICT** | |
| `set_entry_id` | `uuid null` → `station_set_entries.id` **RESTRICT** | |
| `peer_session_id` | `uuid null` → `practice_sessions.id` **RESTRICT** | |
| `source_attempt_id` | `uuid null` → `attempts.id` SET NULL | what a `debrief` is about |
| `definition` | `jsonb null` | the frozen `AssessmentDefinition`, written once on the first successful render — the engine's own document, validated by the engine; storing it relationally would mean re-deriving it to replay |
| `definition_frozen_at` | `timestamptz null` | |
| `room_name` | `varchar(200) null` | |
| `status` | `varchar(32) not null default 'created'` | |
| `started_at` / `completed_at` | `timestamptz null` | |
| `failed_reason` | `varchar(200) null` | |
| `legacy_ref` | `varchar(200) null` | where this row came from in Firestore or b2b, e.g. `b2c:transcript:abc123`; dropped with the `migration` package once every tenant is across |

The four references are `RESTRICT`, not `CASCADE` or `SET NULL`: an attempt is a
recording of something that happened to a person, and deleting the slot it belonged
to must not quietly take the transcript with it. `SET NULL` is not available either,
because the CHECK below requires an `exam_slot` attempt to name its slot.

Constraints:
- CHECK `ck_attempts_kind_matches_reference` — exactly one optional reference matches
  the kind. Written as a CHECK rather than left to the service, because six code paths
  create attempts and only one needs to be wrong for a slot to end up with two live
  attempts.
- CHECK `ck_attempts_status` — `created`, `running`, `interaction_complete`,
  `evaluated`, `failed`. The vocabulary lives in the database as well as in
  `domain.Status`, because `set_status` took a bare string and a typo wrote a status
  nothing would ever match, stalling the attempt in it.
- Partial UNIQUE `uq_attempts_live_slot` on `slot_id` WHERE
  `slot_id IS NOT NULL AND status <> 'failed'` — a slot has at most one attempt that
  has not failed; a re-dispatch fails the old one first.
- Partial UNIQUE `uq_attempts_legacy_ref` WHERE `legacy_ref IS NOT NULL` — a second
  import run updates nothing rather than duplicating history.

Transitions (`domain._ALLOWED`) run `created → running → interaction_complete →
evaluated`, with `failed` reachable throughout; `TERMINAL = {evaluated, failed}`.

### `transcript_messages`
One turn. No `updated_at`: a spoken turn is never edited.

| Field | Type | Notes |
|---|---|---|
| `attempt_id` | `uuid not null` → `attempts.id` CASCADE | indexed with `seq` |
| `message_id` | `varchar(64) not null` | the worker's own id |
| `seq` | `int not null` | |
| `role` | `varchar(16) not null` | |
| `message` | `text not null` | |
| `spoken_at` | `timestamptz not null` | |
| `created_at` | `timestamptz not null default now()` | |

UNIQUE `(attempt_id, message_id)` — chunk posts repeat, because the worker sends them
best-effort and never reads the response.

### `transcripts`
The delivery record for an attempt's turns.

`attempt_id` → `attempts.id` CASCADE (UNIQUE), `complete bool not null default false`,
`runtime_label varchar(64) null`, `delivered_at timestamptz null`.

### `attempt_live_coverage`
One durable live-coverage snapshot per practice attempt. Unlike the base models,
this table has no separate `id` or timestamps.

| Field | Type | Notes |
|---|---|---|
| `attempt_id` | `uuid not null` → `attempts.id` CASCADE | primary key |
| `snapshot` | `jsonb not null` | Engine-validated coverage items and last processed sequence; labels are read from the frozen rubric |

Upserted by serialized `coverage` jobs. Coverage records observed behaviours,
not grades; exam-slot attempts never receive this coaching feed.

### `assessment_results`
What the engine scored, kept immutably.

| Field | Type | Notes |
|---|---|---|
| `attempt_id` | `uuid not null` → `attempts.id` CASCADE | |
| `framework_id` | `varchar(64) not null` | |
| `policy_version` | `varchar(128) not null` | |
| `model_used` | `varchar(64) null` | |
| `payload` | `jsonb not null` | the engine's own output, already validated against its JSON Schema |
| `scored_at` | `timestamptz not null` | |

UNIQUE `(attempt_id, policy_version)`: re-running the same policy stores nothing new,
and scoring under a different one sits beside the old result rather than replacing it.

## results — 3 tables

Ported from b2b's `sql/017`, including the part that matters most: revisions and
events are append-only, **enforced by a trigger** rather than by convention. A
candidate's outcome has to be defensible months later, so the database refuses to let
it be edited at all.

### `candidate_result_revisions`
One version of a decision. Never updated; a change is a new revision. No `updated_at`.

| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid not null` → `organizations.id` CASCADE | |
| `sitting_id` | `uuid not null` → `sittings.id` CASCADE | |
| `trainee_id` | `uuid not null` → `trainees.id` CASCADE | |
| `revision` | `int not null` | CHECK `> 0` |
| `supersedes_revision` | `int null` | |
| `workflow_state` | `varchar(16) not null` | `draft` \| `signed_off` \| `released` |
| `assessment_outcome` | `varchar(16) null` | `pass` \| `fail` \| `inconclusive` \| `withheld` |
| `recruitment_outcome` | `varchar(16) null` | `hired` \| `reserve` \| `not_hired` \| `withdrawn` \| `pending` |
| `rationale` | `text null` | `MAX_RATIONALE = 4000` |
| `moderation_notes` | `text null` | |
| `evidence_snapshot` | `jsonb null` | what the decision was made against |
| `evidence_fingerprint` | `varchar(64) not null` | its hash, so a result signed off against one set of scores is not released after those scores move (`EvidenceChanged`) |
| `disclosure` | `jsonb null` | what the candidate is shown |
| `created_by`, `signed_off_by`, `released_by` | `uuid null` → `users.id` SET NULL | |
| `signed_off_at`, `released_at` | `timestamptz null` | |
| `created_at` | `timestamptz not null default now()` | |

UNIQUE `(sitting_id, trainee_id, revision)`; index `(org_id, sitting_id, trainee_id)`.
CHECKs also enforce that a `signed_off` revision names its signer and a `released` one
names its releaser, so an incomplete record cannot be written. Assessment and
recruitment outcomes are cross-checked in `domain._COMPATIBLE`.

### `candidate_result_events`
What happened to a decision, append-only. No `updated_at`.

`revision_id` → `candidate_result_revisions.id` CASCADE (indexed),
`event_type varchar(32) not null`, `actor_user_id` → `users.id` SET NULL,
`idempotency_key varchar(200) not null unique`, `at timestamptz not null default now()`.

### `candidate_result_notifications`
Outbox for telling a candidate — a row rather than an email sent inline, so a release
is not lost because a mail provider was briefly down.

| Field | Type | Notes |
|---|---|---|
| `event_id` | `uuid not null` → `candidate_result_events.id` CASCADE | |
| `channel` | `varchar(16) not null default 'email'` | |
| `recipient` | `varchar(320) not null` | |
| `template_key` | `varchar(64) not null` | |
| `payload` | `jsonb null` | |
| `idempotency_key` | `varchar(200) not null unique` | |
| `status` | `varchar(16) not null default 'pending'` | |
| `attempts` | `int not null default 0` | |
| `available_at` | `timestamptz not null default now()` | partial index WHERE `status = 'pending'` |
| `delivered_at` | `timestamptz null` | |
| `last_error` | `text null` | |

## reviews — 3 tables

b2b keeps all three of these in one wide table discriminated by a `feedback_kind`
column, with no foreign keys at all. Three tables here, each with real keys, because
they have different owners, lifecycles and uniqueness.

`RAG_VALUES = (R, A, G)`, `REVIEW_STATUSES = (draft, completed)`.

### `slot_reviews`
A rubric filled in against one slot, by staff or by a peer observer.

| Field | Type | Notes |
|---|---|---|
| `slot_id` | `uuid not null` → `slots.id` CASCADE | |
| `org_id` | `uuid not null` → `organizations.id` CASCADE | indexed |
| `submitted_by` | `uuid not null` → `users.id` CASCADE | |
| `observer_trainee_id` | `uuid null` → `trainees.id` SET NULL | set when a trainee reviews a peer rather than staff reviewing them |
| `status` | `varchar(16) not null default 'draft'` | |
| `field_values` | `jsonb not null default {}` | a selection over the bound feedback template, whose shape the org defines |
| `notes` | `text null` | |
| `completed_at` | `timestamptz null` | |

UNIQUE `(slot_id, submitted_by)` — one review per person per slot; submitting twice
edits the first.

### `gp_lead_reviews`
A revisioned second opinion on a slot. One per slot, edited in place, with a revision
counter because two reviewers can hold the same screen open (`ReviewConflict`).

`slot_id` → `slots.id` CASCADE (UNIQUE), `org_id` → `organizations.id` CASCADE,
`revision int not null default 1`, `status varchar(16) not null default 'draft'`,
`overall_rag varchar(1) null`, `field_values jsonb not null default {}`,
`notes text null`, `reviewed_by` → `users.id` SET NULL, `completed_at timestamptz null`.

### `circuit_reviews`
What a supervisor finalises for a whole circuit.

`circuit_id` → `circuits.id` CASCADE (UNIQUE), `org_id` → `organizations.id` CASCADE,
`merged_notes text null`, `contributions jsonb null`, `finalized_at timestamptz null`,
`finalized_by` → `users.id` SET NULL.

---

# Institutions running exams

## sittings — 6 tables

Domain bounds: `EXAM_MAX_STATIONS = 12`, `DEFAULT_READING_MINUTES = 3`,
`DEFAULT_SIMULATION_MINUTES = 10`, `READING_BOUNDS = (1, 30)`,
`SIMULATION_BOUNDS = (1, 180)`.

### `sittings`
A scheduled event an organisation holds.

| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid not null` → `organizations.id` CASCADE | indexed with `status` |
| `programme_id` | `uuid null` → `org_programmes.id` SET NULL | |
| `cohort_id` | `uuid null` → `cohorts.id` SET NULL | |
| `name` | `varchar(200) not null` | |
| `scheduled_for` | `timestamptz null` | |
| `mode` | `varchar(16) not null default 'training'` | `training` \| `exam` — the B2B exam arm |
| `sitting_type` | `varchar(32) not null default 'group_training'` | |
| `status` | `varchar(32) not null default 'scheduled'` | `scheduled` → `in_progress` when a circuit starts → `completed` when every circuit on it has ended (D-7). A circuit that was never started holds it open; ending that circuit outright is what closes the sitting |
| `rubric_version_id` | `uuid **not null**` → `rubric_versions.id` RESTRICT | resolved from the sitting's `programme_id` at create time: the programme's exam must name a published rubric version. Replaces the former `feedback_template_version_id` binding |

### `circuits`
| Field | Type | Notes |
|---|---|---|
| `sitting_id` | `uuid not null` → `sittings.id` CASCADE | |
| `org_id` | `uuid not null` → `organizations.id` CASCADE | |
| `name` | `varchar(200) not null` | |
| `supervisor_user_id` | `uuid null` → `users.id` SET NULL | |
| `timing` | `jsonb null` | a closed shape with a handful of fields, kept as JSON because the break list is variable-length and read as a unit (`domain.Timing`, `domain.Break`) |
| `active_slot_id` | `uuid null` | deliberately not a FK — it points into `slots`, which points back |
| `room_name` | `varchar(200) null` | |
| `agent_dispatched_at` | `timestamptz null` | |
| `started_at` / `ended_at` | `timestamptz null` | partial index `(org_id) WHERE started_at IS NOT NULL AND ended_at IS NULL` — the exam-day board's query |
| `phase` | `varchar(16) null` | `reading`, `simulation` or `break`; null when nothing is running. CHECK `ck_circuits_phase` |
| `phase_started_at` / `phase_ends_at` | `timestamptz null` | the one deadline every screen reads |
| `phase_seq` | `int not null default 0` | bumped by every transition and every override |
| `paused_at` | `timestamptz null` | set while the clock is stopped |
| `paused_seconds` | `int not null default 0` | total time this phase spent paused, so elapsed excludes it |
| `auto_advance` | `boolean not null default true` | off means a human decides every move |

**The examination clock is here, not on the slot.** A break belongs to no slot —
it is the circuit resting between stations — and that is the one thing a per-slot
clock could not express, which is why breaks were stored and counted down by
nobody. A pause has the same shape: stopping the clock must rewrite one deadline,
and with the clock on two rows it rewrote two.

`phase_seq` is how a human beats the clock. Every transition is a job scheduled
for the moment the phase ends, carrying the sequence it was scheduled against;
any override bumps the sequence, so the job it raced arrives holding a number
that no longer matches and does nothing. That is the whole concurrency design —
no lease, no claim table, one integer.

### `circuit_interventions`
What a human did to a running examination, and why. Append-only, and no
`updated_at`: an intervention is a fact about a moment, not a row anybody edits.
When a candidate says their station went wrong, the question is what was done to
it and by whom, and before this the answer was nowhere.

| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid not null` → `organizations.id` CASCADE | |
| `circuit_id` | `uuid not null` → `circuits.id` CASCADE | indexed with `at` |
| `slot_id` | `uuid null` → `slots.id` SET NULL | null for an override about the circuit rather than one station |
| `actor_user_id` | `uuid null` → `users.id` SET NULL | SET NULL, not CASCADE: removing a member must not delete the record that they extended a candidate's clock |
| `action` | `varchar(32) not null` | `pause`, `resume`, `extend_clock`, `reset_clock`, `resend_patient`, `redo_station`, `jump_to`, `advance`, `auto_advance` |
| `reason` | `text null` | free text, because the reasons are the ones nobody predicted |
| `phase_seq_before` / `phase_seq_after` | `int not null` | places the intervention against the transition it displaced |
| `at` | `timestamptz not null` | |

### `circuit_stations`
Replaces b2b's `station_refs jsonb`. A real row per station, so a station cannot be
deleted out from under a circuit and "which circuits use this station?" is a query.
No `updated_at`.

`circuit_id` → `circuits.id` CASCADE, `position int not null`,
`station_version_id` → `station_versions.id` RESTRICT.
UNIQUE `(circuit_id, position)`.

### `circuit_trainees`
Replaces b2b's `trainee_ids text[]`. No `updated_at`.

`circuit_id` → `circuits.id` CASCADE, `trainee_id` → `users.id` CASCADE,
`position int not null`. UNIQUE `(circuit_id, trainee_id)`.

### `slots`
One trainee at one station. Carries no transcript and no feedback: those live on the
attempt, which is what makes a re-dispatch keep the first recording instead of
overwriting it. The id is globally unique because the worker and several routes
address a slot directly; every user-facing route still resolves `org_id` from the row.

| Field | Type | Notes |
|---|---|---|
| `circuit_id` | `uuid not null` → `circuits.id` CASCADE | |
| `org_id` | `uuid not null` → `organizations.id` CASCADE | indexed with `status` |
| `slot_index` | `int not null` | |
| `trainee_id` | `uuid not null` → `users.id` CASCADE | indexed |
| `station_version_id` | `uuid not null` → `station_versions.id` RESTRICT | |
| `status` | `varchar(32) not null default 'scheduled'` | `scheduled` → `reading` → `in_consultation` → `completed`, or `skipped`. CHECK `ck_slots_status` |
| `room_name` | `varchar(200) null` | |
| `started_at` / `ended_at` | `timestamptz null` | |
| `exam_completed_at` | `timestamptz null` | |

UNIQUE `(circuit_id, slot_index)`.

`status` and the three timestamps were written by nothing at all while four read
models displayed them, which is why a finished station kept offering a join
button. The orchestrator owns them now. `skipped` is a station the circuit moved
past — jumped over, or left unsat when the examination ended early. It is not
`completed`, because nothing was recorded, and not `scheduled`, because it is not
coming.

A slot carries no clock. That is the circuit's: see `circuits` above.

## roster — 4 tables

### `cohorts`
`org_id` → `organizations.id` CASCADE, `name varchar(200) not null`,
`academic_year varchar(32) null`, `status varchar(32) not null default 'active'`.
UNIQUE `(org_id, name)`.

### `trainees`
Someone an organisation teaches. Separate from `users` because an institution rosters
people before they have ever signed in — `user_id` is filled when they do.

| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid not null` → `organizations.id` CASCADE | indexed with `cohort_id` |
| `user_id` | `uuid null` → `users.id` SET NULL | filled on first sign-in |
| `email` | `citext not null` | |
| `first_name` / `last_name` | `varchar(100) null` | |
| `cohort_id` | `uuid null` → `cohorts.id` SET NULL | |
| `access_revoked_at` | `timestamptz null` | raises `TraineeRevoked` |
| `anonymised_at` | `timestamptz null` | GDPR erasure for a row `DELETE` refuses (`trainee_in_use`) — `service_edit.anonymise_trainee` scrubs `email`/`first_name`/`last_name` and sets this, keeping any decision on record |

UNIQUE `(org_id, email)`.

### `trainee_groups`
| Field | Type | Notes |
|---|---|---|
| `org_id` | `uuid not null` → `organizations.id` CASCADE | |
| `label` | `varchar(200) not null` | |
| `label_normalized` | `varchar(200) not null` | stored so the uniqueness constraint means what people expect: "Cohort A" and "cohort a" are one group |

UNIQUE `(org_id, label_normalized)`.

### `trainee_group_members`
The table b2b does not have. Without it, membership is a string match between a
trainee's cohort and a group's label, recomputed on every circuit build: renaming a
group empties it, two groups sharing a label collide, and nobody can be in two groups.

`group_id` → `trainee_groups.id` CASCADE, `trainee_id` → `trainees.id` CASCADE
(indexed). UNIQUE `(group_id, trainee_id)`.

---

# Access, money and growth

## entitlements — 1 table

### `entitlements`
A record of access, separate from whatever caused it. Append-only in practice:
revoking sets `revoked_at` rather than deleting the row, so "why could they do that?"
stays answerable after the fact, and a refund can revoke access without erasing the
payment that bought it.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | |
| `exam_id` | `uuid not null` → `exams.id` RESTRICT | |
| `source` | `varchar(32) not null` | CHECK: `purchase` \| `org_grant` \| `trial` \| `sso_tenant` \| `admin` |
| `source_ref` | `varchar(200) null` | whatever caused the grant: a payment id, a membership id, a tenant slug |
| `org_id` | `uuid null` → `organizations.id` CASCADE | |
| `starts_at` | `timestamptz not null default now()` | |
| `ends_at` | `timestamptz null` | |
| `revoked_at` | `timestamptz null` | |
| `granted_by` | `uuid null` → `users.id` SET NULL | |

Partial index `ix_entitlements_live` on `(user_id, exam_id)` WHERE
`revoked_at IS NULL` — the only lookup the access check performs.
Domain: `ALLOWED_TRIAL_STATIONS = 3`, `TRIAL_DAYS = 14`.

## billing — 3 tables

### `plans`
What a Stripe price buys. A row rather than a hardcoded table keyed by pence: b2c
matches the amount paid against `PRICE_CONFIG` and raises on a miss, so changing a
price — or taking a payment in another currency, or honouring a Stripe coupon —
breaks the purchase *after* the card has been charged.

| Field | Type | Notes |
|---|---|---|
| `code` | `varchar(32) not null unique` | `one_month` \| `three_month` \| `six_month` |
| `stripe_price_id` | `varchar(100) not null unique` | |
| `exam_code` | `varchar(32) null` | |
| `amount_pence` | `int not null` | |
| `currency` | `varchar(3) not null default 'gbp'` | |
| `duration_days` | `int not null` | `DEFAULT_PLAN_DAYS = {one_month: 30, three_month: 90, six_month: 180}` |
| `active` | `bool not null default true` | |

### `stripe_events`
Every webhook delivery we have acted on — the thing b2c has no equivalent of. Stripe
retries until it gets a 2xx, and without this a retry re-runs the grant. No
`updated_at`.

| Field | Type | Notes |
|---|---|---|
| `event_id` | `varchar(100) not null unique` | |
| `event_type` | `varchar(100) not null` | `ACCESS_GRANTING_EVENTS = {checkout.session.completed}` |
| `received_at` | `timestamptz not null default now()` | |
| `processed_at` | `timestamptz null` | |
| `payload` | `jsonb null` | |
| `failure` | `text null` | why a delivery was received but not applied: an address with no account, a price with no plan. Kept rather than rolled back, so it can be reconciled by hand or applied by Stripe's next retry once fixed |

### `payments`
| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` **RESTRICT** | a payment outlives the account |
| `plan_id` | `uuid null` → `plans.id` SET NULL | |
| `stripe_payment_intent_id` | `varchar(100) not null unique` | |
| `checkout_session_id` | `varchar(100) null` | |
| `amount_total_pence` | `int not null` | |
| `currency` | `varchar(3) not null` | |
| `receipt_url` | `varchar(500) null` | |
| `paid_at` | `timestamptz not null` | |
| `entitlement_id` | `uuid null` → `entitlements.id` SET NULL | the entitlement this payment bought; nullable because a refund revokes the entitlement without deleting either record |
| `receipt_id` | `varchar(32) null unique` | our own receipt number, minted when the webhook records the payment. Null for payments taken before receipts existed: those stay Stripe-only until a backfill decides otherwise |
| `customer_email` / `customer_name` | `varchar(320) null` / `varchar(200) null` | frozen at payment. A receipt shows who paid at the time, not who the account belongs to now |
| `amount_tax_pence` | `int not null default 0` | |
| `plan_starts_at` / `plan_ends_at` | `timestamptz null` | the window the payment bought, frozen so a later change to the plan cannot rewrite a document already sent |

## growth — 5 tables

`PILOT_PARTNERS = {bmj}`, `PILOT_EXAMS = (sca, plab, ortho)`,
`ATTRIBUTION_WINDOW = 90 days`, landing paths under `/exams/`.

### `partner_arrivals`
Somebody landing here from a partner's link.

| Field | Type | Notes |
|---|---|---|
| `partner` | `varchar(32) not null` | indexed with `landed_at` |
| `exam_code` | `varchar(32) null` | |
| `visitor_key` | `varchar(64) not null` | anonymous until they sign up; this is what links the two. Indexed |
| `ref_id` | `varchar(64) null` | |
| `landing_path` | `varchar(300) null` | |
| `utm` | `jsonb null` | |
| `landed_at` | `timestamptz not null default now()` | |

### `acquisitions`
The partner a user was acquired through, decided once. Immutable by intention:
re-attributing an existing user because they later clicked another link is how a
partner's numbers stop being reconcilable.

`user_id` → `users.id` CASCADE (UNIQUE), `partner varchar(32) not null`,
`exam_code varchar(32) null`, `arrival_id` → `partner_arrivals.id` SET NULL,
`acquired_at timestamptz not null default now()`.

### `partner_reporters`
Someone allowed to read one partner's numbers, and nothing else.
`partner varchar(32) not null`, `email citext not null`, `revoked_at timestamptz null`.
UNIQUE `(partner, email)`.

### `referrals`
`referrer_user_id` → `users.id` CASCADE (indexed), `code varchar(32) not null unique`,
`referred_user_id` → `users.id` SET NULL, `redeemed_at timestamptz null`,
`earned_pence int not null default 0`, `plan_code varchar(64) null` — the
redeeming purchase's plan, carried onto the row so `GET /me/referrals/history`
(A2) can show "Subscription type (referee)" without a join back through
billing. A row with no `redeemed_at` is a
person's shareable code, reusable as in b2c; each purchase made with it is its
own redeemed row coded `<CODE>-<suffix>`. Settlement happens outside the product;
these four are the record of whether it has: `payout_status varchar(16) not
null default 'unpaid'` (indexed with `redeemed_at IS NOT NULL`, since the
settlement queue never asks about a code nobody has used), `paid_at
timestamptz null`, `paid_by_user_id` → `users.id` SET NULL, and
`payout_reference varchar(64) null` — the bank transfer's own reference.

### `referral_payout_details`
Where a referrer sits the bank details settlement pays out to (A1), added
because the retiring client's Settings screen collects them but nothing here
stored them. `user_id` → `users.id` CASCADE (UNIQUE — one set of details per
person), `bank_name varchar(200) not null`, `account_holder_name varchar(200)
not null`, `sort_code_ciphertext text not null`, `account_number_ciphertext
text not null`. The sort code and account number are Fernet-encrypted at rest
(`app.core.secrets_at_rest`, key `PAYOUT_DETAILS_KEY`) and never stored in the
clear: `GET /me/referral-payout-details` decrypts and returns the full sort
code (it only identifies a bank branch) but masks the account number to its
last 4 digits; the platform admin settlement queue
(`ReferralAdminRead.payout_details`) is the only reader that sees the account
number decrypted in full.

---

# Consumer social features

## community — 2 tables

One `posts` table with a self-referencing parent rather than separate question, reply
and comment tables: they are the same shape, and b2c's three near-identical
collections per product (twelve in total) is what happens otherwise.

### `posts`
Carries the `Addressed` columns (`visibility`, `audience_org_id`, `audience_group_id`).

| Field | Type | Notes |
|---|---|---|
| `kind` | `varchar(16) not null` | `question` \| `reply` \| `comment` |
| `parent_id` | `uuid null` → `posts.id` CASCADE | indexed |
| `author_id` | `uuid not null` → `users.id` CASCADE | |
| `exam_id` | `uuid null` → `exams.id` SET NULL | indexed with `created_at` |
| `station_id` | `uuid null` → `stations.id` CASCADE | a comment about a specific station, which b2c keeps in its own collection. Indexed |
| `title` | `varchar(300) null` | |
| `body` | `text not null` | `MAX_CONTENT = 10_000` |
| `tags` | `jsonb not null default '[]'` | a question's tags — ≤ 5 normalized lowercase keys, ≤ 32 chars each (`domain.clean_tags`). GIN-indexed (`ix_posts_tags`) for the feed's `tag` containment filter. Replies and comments carry `[]` |
| `removed_at` / `removed_by` | `timestamptz null` / `uuid null` → `users.id` SET NULL | |

CHECK `ck_posts_parent_matches_kind`: a question starts a thread (no parent), a reply
sits under a post, a comment sits under a station (no parent, station required). The
first version of this said "anything but a question has a parent", which made every
station comment a constraint violation. Plus CHECK `AUDIENCE_CHECK` and indexes on
`(audience_org_id, created_at)` and `(audience_group_id, created_at)`, which the list
query filters on before anything else.

### `post_likes`
Who liked what. A row rather than a counter on the post: b2c increments a number, so a
double tap counts twice and nothing can be undone.

`post_id` → `posts.id` CASCADE, `user_id` → `users.id` CASCADE.
UNIQUE `(post_id, user_id)`.

## marketplace — 2 tables

`JOIN_WINDOW = 10 minutes`, `CLAIMABLE_STATUSES = {available}`,
`CANCELLABLE_STATUSES = {available, claimed}`.

### `availability_posts`
A time someone is free to practise with a peer. Carries the `Addressed` columns.

| Field | Type | Notes |
|---|---|---|
| `owner_user_id` | `uuid not null` → `users.id` CASCADE | indexed |
| `exam_id` | `uuid not null` → `exams.id` RESTRICT | |
| `starts_at` | `timestamptz not null` | partial index WHERE `status = 'available'` |
| `duration_minutes` | `int not null default 30` | |
| `note` | `text null` | |
| `status` | `varchar(16) not null default 'available'` | |
| `claimed_by_user_id` | `uuid null` → `users.id` SET NULL | |
| `claimed_at` / `cancelled_at` | `timestamptz null` | |

### `peer_sessions`
The session a claim creates. Two people, one room, one appointed time.

`post_id` → `availability_posts.id` SET NULL (nullable),
`owner_user_id` and `claimer_user_id` → `users.id` CASCADE (indexed together),
`exam_id` → `exams.id` RESTRICT, `starts_at timestamptz not null`,
`room_name varchar(200) null`, `status varchar(16) not null default 'scheduled'`,
`practice_session_id` → `practice_sessions.id` SET NULL (nullable — filled once the
matched pair opens their LiveKit room), `doctor_user_id` and `patient_user_id` →
`users.id` SET NULL (nullable — the two roles are appointed when the session
starts, not when it is scheduled), `ended_at timestamptz null`,
`cancelled_at timestamptz null`.

## peer_practice — 3 tables

### `practice_queue_entries`
Someone waiting to be paired. Carries the `Addressed` columns.

| Field | Type | Notes |
|---|---|---|
| `seq` | `bigint not null unique`, `GENERATED … AS IDENTITY` | a queue is ordered by arrival, and `created_at` cannot express that: everyone joining in one transaction shares a `now()`, and breaking the tie on a random uuid gives a stable order that is not the order they arrived in |
| `user_id` | `uuid not null` → `users.id` CASCADE | |
| `exam_id` | `uuid not null` → `exams.id` RESTRICT | |
| `status` | `varchar(16) not null default 'waiting'` | |
| `matched_session_id` | `uuid null` | not a FK |
| `left_at` | `timestamptz null` | |
| `expires_at` | `timestamptz null` | a waiting entry's own deadline; distinct from `left_at` which is when the person actually left |

Partial UNIQUE on `(user_id, exam_id)` WHERE `status = 'waiting'` — one live place per
person per exam; joining twice keeps the place you already have. Partial index on
`(exam_id, seq)` WHERE `status = 'waiting'` is the matcher's read.

### `practice_sessions`
Two people practising, one as doctor and one as patient.

`exam_id` → `exams.id` RESTRICT, `doctor_user_id` and `patient_user_id` → `users.id`
CASCADE (indexed together), `station_version_id` → `station_versions.id` SET NULL,
`peer_session_id` → `peer_sessions.id` SET NULL (the marketplace claim that
started this — `use_alter` because `peer_sessions` itself points back here),
`room_name varchar(200) null`, `status varchar(16) not null default 'matched'`,
`current_phase varchar(16) null` (the phase the session is in — preparation,
consultation, feedback — driven by the circuit clock), `phase_ends_at timestamptz null`,
`doctor_joined_at` / `patient_joined_at` / `preparation_started_at timestamptz null`
(per-participant timing), `started_at` / `ended_at timestamptz null`,
`end_reason varchar(32) null`, `feedback_rating int null`,
`feedback_comment varchar(2000) null`, `would_practice_again bool null`.

The accept handshake: a matched pair starts `status='pending_accept'` rather
than joinable, with `accept_expires_at timestamptz null` — 120 seconds after
the match, past which a still-silent side's pairing times out
(`end_reason='no_response'`). `doctor_accepted_at` / `patient_accepted_at
timestamptz null` record when each side accepted; once both are set the
session becomes `status='matched'`. A decline before both accept ends the
session with `end_reason='declined'`. Both are null for a marketplace-booked
pair (`peer_session_id` set), which skips the handshake and starts `matched`
straight away — the pair already agreed to a fixed time when they booked it.

Recording and feedback: `egress_id varchar(128) null` (the LiveKit Egress the stop has
to find), `recording_key varchar(512) null` (the S3 object key — the URL is presigned
on demand, never stored), `recording_state varchar(16) not null default 'none'`
(`none` | `recording` | `stopped` | `failed`; a recording that started and never
stopped is otherwise invisible), `recording_error varchar(200) null`,
`doctor_attempt_id` → `attempts.id` SET NULL — the doctor's scored `kind='peer'`
attempt. It is the readable half of the link `attempts.peer_session_id` already
provides in the other direction; without it the session read cannot tell the client
where its feedback is without a reverse scan. Only the doctor is marked: the rubric is
written for the doctor's performance, so the patient's session carries no attempt.

Partial index `ix_practice_sessions_recording_state` on `recording_state` WHERE
`recording_state <> 'none'` — a session that was never recorded is the uninteresting
majority, and the transcription job only ever asks after the rest.

### `practice_history`
What part someone last played, and how often they have practised. A row rather than
fields on the user: it is peer-practice's business, and b2c putting it on the user
document is why the matcher reaches into four different collections to find it.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE, UNIQUE | |
| `last_role` | `varchar(16) null` | `doctor` \| `patient` |
| `session_count` | `int not null default 0` | |
| `never_doctor` | `bool not null default false` | replaces b2c's hardcoded list of three personal email addresses |

## assistant — 2 tables

### `assistant_sessions`
One conversation where the assistant helps someone use the product.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | indexed with `created_at` |
| `session_type` | `varchar(32) not null` | `help` \| `onboarding` \| `dashboard` \| `consulting-doctor` (alias: `athena-doctor`) |
| `instructions` | `text not null` | rendered backend-side, exactly as an attempt's are — the worker holds no templates and is handed finished text |
| `greeting` | `text null` | |
| `room_name` | `varchar(200) null` | |
| `status` | `varchar(16) not null default 'active'` | `JOINABLE_STATUSES = {active}` |
| `extras` | `jsonb null` | |
| `started_at` / `completed_at` | `timestamptz null` | |
| `end_reason` | `varchar(64) null` | |
| `usage` | `jsonb null` | |

### `assistant_transcript_messages`
Turns, kept only for `help` sessions (`_KEEPS_TRANSCRIPT`). The other three kinds are
navigation; storing them would collect recordings of people's screens for nothing.
No `updated_at`.

Same shape as `transcript_messages`: `session_id` → `assistant_sessions.id` CASCADE,
`message_id varchar(64)`, `seq int`, `role varchar(16)`, `message text`,
`spoken_at timestamptz`, `created_at timestamptz default now()`.
UNIQUE `(session_id, message_id)`; index `(session_id, seq)`.

## tutor_memory — 3 tables

What the tutor knows about one learner. Sits above `assistant` and `attempts`; both
announce their moments through `bind_*` seams, so nothing below imports this.

### `learning_events`
One thing this person read, practised or listened to. Written by the browser as it
happens: a summary opened in the app leaves no other trace, and the tutor asking how
it went is the point of collecting them.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | indexed with `occurred_at` |
| `exam_id` | `uuid null` → `exams.id` RESTRICT | an exam outlives any learner; deleting one should fail loudly, not quietly erase everybody's history of studying for it |
| `kind` | `varchar(16) not null` | CHECK `viewed` \| `practised` \| `listened` |
| `ref_kind` | `varchar(24) not null` | CHECK `summary` \| `slide_deck` \| `podcast` \| `blog` \| `station` \| `management_plan` |
| `ref_id` | `varchar(120) not null` | a string, not a foreign key: the six kinds live in three slices and one is not a row at all. Resolving a ref into a screen is the frontend's |
| `title` | `varchar(300) not null` | what the tutor will call it out loud |
| `occurred_at` | `timestamptz not null` | |
| `meta` | `jsonb null` | |
| `created_at` | `timestamptz not null default now()` | no `updated_at`: an event happened once |

Index `(user_id, ref_kind, ref_id, occurred_at)` is the dedup read: two sightings of
the same thing inside ten minutes are one visit, because somebody who opens a summary,
follows a link and comes back has not read it twice.

### `tutor_notes`
Something the tutor wrote down: how a conversation ended, or a fact it was told. Two
kinds in one table because they are read together and forgotten together.

| Field | Type | Notes |
|---|---|---|
| `user_id` | `uuid not null` → `users.id` CASCADE | indexed with `created_at` |
| `exam_id` | `uuid null` → `exams.id` RESTRICT | |
| `session_id` | `uuid null` → `assistant_sessions.id` SET NULL | **not** CASCADE: the summary is what survives the conversation, and the turns are deleted on purpose once it is written |
| `kind` | `varchar(24) not null` | CHECK `session_summary` \| `stated_fact` |
| `body` | `jsonb not null` | `session_summary`: `{summary, agreed_next_steps[], topics[]}`. `stated_fact`: `{fact}`, clipped to 300 characters — longer and it stops being a fact and becomes a paragraph the tutor recites |
| `created_at` | `timestamptz not null default now()` | |

### `debrief_summaries`
What a debrief concluded and what was agreed about it.

| Field | Type | Notes |
|---|---|---|
| `attempt_id` | `uuid not null` → `attempts.id` CASCADE | UNIQUE. Enforced here rather than by the job checking first: the queue may deliver twice, and two summaries would have the tutor agreeing two different plans |
| `user_id` | `uuid not null` → `users.id` CASCADE | indexed with `created_at` |
| `exam_id` | `uuid null` → `exams.id` RESTRICT | |
| `key_insights` | `jsonb not null` | list of strings |
| `action_plan` | `jsonb not null` | `[{text, done}]`. The flag is what lets the tutor ask about a step by name and hear whether it happened |
| `narrative` | `text null` | |
| `model_used` | `varchar(64) null` | |
| `created_at` | `timestamptz not null default now()` | |

### `material_chunks`
The study material cut into passages, with the vector each is retrieved by. Derived
data entirely: every row is rebuilt from `station_versions` and `media_items` by the
nightly `reindex_material` job, which is why dropping this table loses nothing but
the time to run it again. Owned by `tutor_memory` rather than by the slices the text
comes from — a rebuildable index belongs to the reader that needs it, not to the
slice that owns the source of truth. See ADR 0019.

| Field | Type | Notes |
|---|---|---|
| `corpus` | `varchar(24) not null` | CHECK `station` \| `summary` \| `slide_deck` \| `podcast` \| `blog` |
| `source_id` | `varchar(120) not null` | A string, not a foreign key: the corpora live in different slices, and a key per corpus would make adding a third one a schema change. The re-index retires a deleted source's passages on its next run, which is the honest cost |
| `exam_id` | `uuid null` → `exams.id` CASCADE | Indexed with `corpus`. CASCADE, unlike the other tutor tables' RESTRICT: those hold somebody's history and must not vanish quietly, while this holds a copy of a catalogue being deleted — and passages of an exam nobody can buy are passages nobody may be read |
| `title` | `varchar(300) not null` | what a citation says |
| `section` | `varchar(40) not null` | the heading the passage was found under, or `management` for the tail |
| `chunk_index` | `integer not null` | UNIQUE with `corpus` + `source_id`, which is what `upsert` writes against so a re-index replaces rather than duplicates |
| `text` | `text not null` | the passage the tutor quotes |
| `embedding` | `vector(1536) not null` | `text-embedding-3-small`. IVFFlat index with `vector_cosine_ops`, `lists = 100` — the operator class must match the `<=>` the query uses or the index is not consulted. The width is DDL, so changing the model means re-embedding everything |
| `indexed_at` | `timestamptz not null default now()` | |

## notifications — 1 table

### `outbound_messages`
One outbox rather than one per slice: a message is a message, and a single queue is
the only way "what is stuck?" has one answer.

| Field | Type | Notes |
|---|---|---|
| `channel` | `varchar(16) not null default 'email'` | |
| `recipient` | `varchar(320) not null` | |
| `subject` | `varchar(300) not null` | |
| `template_key` | `varchar(64) not null` | |
| `payload` | `jsonb null` | |
| `idempotency_key` | `varchar(200) not null unique` | written by the slice that needed it, so the key is that slice's business. A repeat is a no-op rather than a second email |
| `status` | `varchar(16) not null default 'pending'` | `pending` → `processing` → delivered |
| `attempts` | `int not null default 0` | `MAX_ATTEMPTS = 6` |
| `available_at` | `timestamptz not null default now()` | partial index WHERE `status = 'pending'` — the due query |
| `claimed_at` | `timestamptz null` | when a worker took this message. Partial index WHERE `status = 'processing'` — the reaper's query |
| `delivered_at` | `timestamptz null` | |
| `last_error` | `text null` | |

A crash between claiming and sending left `processing` rows that the due index cannot
see and nothing ever looked at again; a claim older than `CLAIM_TIMEOUT_SECONDS = 600`
is taken back. Retry backoff: `BASE_RETRY_SECONDS = 30`, capped at
`MAX_RETRY_SECONDS = 3600`.

---

# Voice routing

`voice` owns no tables. Its domain decides which worker family and which LiveKit
deployment a session belongs to, from a session type:

- `Family.ASSESSMENT` — `conversation`, `admin-test`, `debrief`
- `Family.ASSISTANT` — `help`, `onboarding`, `dashboard`, `consulting-doctor`
- `Mode.SELF_HOSTED` / `Mode.LIVEKIT_CLOUD`

---

# Cross-cutting patterns

**Versions are frozen, references point at versions.** `station_versions`,
`station_template_versions` and `feedback_template_versions` are immutable once
published. Everything that records what somebody was assessed on — `attempts`,
`slots`, `circuit_stations`, `station_set_entries`, `practice_sessions` — holds a
`station_version_id`, never a `station_id`.

**Delete rules carry meaning.** `RESTRICT` where a row is evidence (an attempt's
slot, a station version anything was sat against, a payment's user). `CASCADE` where
the child has no meaning without the parent (an org's memberships, a post's likes).
`SET NULL` where the reference is attribution that can survive the loss of the actor
(`published_by`, `signed_off_by`, `removed_by`).

**Idempotency is a column, not a convention.** `stripe_events.event_id`,
`outbound_messages.idempotency_key`, `candidate_result_events.idempotency_key`,
`transcript_messages.(attempt_id, message_id)`, `attempts.legacy_ref`.

**Partial unique indexes carry the "only one live X" rules.** One non-failed attempt
per slot, one waiting queue entry per person per exam, one entitlement lookup per
user and exam.

**Vocabularies live in the database where getting one wrong is silent.**
`attempts.status`, `attempts.kind` and its reference matching,
`entitlements.source`, `candidate_result_revisions.workflow_state` and its
signer/releaser rules, the three `AUDIENCE_CHECK` tables, `stations.owner_kind`.
Other status columns are enforced in the domain layer only.

**JSON is used in five places, each on purpose**: `station_versions.content` and
`rubric_versions.structure` (org-authored shapes with no fixed columns),
`attempts.definition` and `assessment_results.payload` (the engine's own documents,
already schema-validated), `feedback_template_versions.field_selection` (a selection
over a document), `circuits.timing` (a closed shape read as a unit),
`media_items.content` (differs by kind), plus small metadata bags
(`audit_log.metadata`, `partner_arrivals.utm`, `*_notifications.payload`).
