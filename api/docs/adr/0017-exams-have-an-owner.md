# 0017. An exam has an owner; an institution authors its own

Date: 2026-09-18
Status: accepted

Extends 0011 (`exams` and `org_programmes` are two tables) and 0016 (exams and rubrics are
authored data). Neither is reversed: the two tables stay two tables, and an exam stays a row
somebody writes rather than shipped code.

## Context
0011 settled that a platform exam and an org programme are different things, and 0016 made the
exam itself authored rather than seeded. Both left one assumption in place that neither examined:
an exam is *ours*. `exams` had no owner column, so the only exam an institution could run was one
the platform had published, and `POST /orgs/{slug}/programmes` resolved a code out of a global
catalogue we controlled.

That makes the B2B arm a dependant of the B2C catalogue. A medical school's finals OSCE is not
our product, and the school should not be waiting on us to write a row before it can assess
against it. It also reads badly the other way: the four exams we publish are consumer products,
and there is no reason an institution's private assessment should be able to appear in them.

The restriction was invisible because it was structural rather than enforced — there was no rule
to read, just a table that had never been given an owner.

## Decision
`exams` gains `owner_kind` (`platform` | `org`) and a nullable `org_id`, the same split
`stations` and `rubrics` already carry, with the same CHECK tying them together.

- A **platform** exam is the consumer catalogue. `GET /exams` lists it and nothing else.
- An **org** exam is that institution's own, authored through `POST /orgs/{slug}/exams`,
  published and retired on its own schedule, and invisible outside it.
- `code` is unique **within an owner**, not globally: a partial unique index per half.
- Reading is wider than writing. An org resolves its own exams plus the platform's published
  ones; the platform resolves only its own. Drafts are visible to their owner alone, in both
  directions. Only an owner may edit, publish or retire its own exam, and a stranger's exam is
  refused as `unknown_exam` rather than `forbidden`.
- `resolve_exam` takes the caller's scope, defaulting to the platform. The consumer surfaces —
  peer queue, marketplace, community, media, the station library — pass no org, so a school's
  private exam code is unreachable from outside it.
- A programme still names an exam, now either kind. It remains what 0011 made it: the label a
  year's sittings are grouped under, carrying no content.

## Consequences
- An institution onboards without the platform writing anything for it. That was the point.
- Two schools may both have a `finals`, and a school may have its own `plab` beside ours; its own
  wins when a code is resolved in its scope.
- An org exam may name its own published rubric. A platform exam still may not — it belongs to
  everyone, so it cannot bind one institution's rubric — but the reverse restriction is lifted,
  because otherwise authoring an exam would still mean waiting for us to write the rubric.
- `partner_pilot` is consumer-side and is forced false on an org exam: a partner attribution link
  is a B2C funnel.
- The two lifecycles are genuinely independent. Retiring our PLAB leaves every institution's
  programmes and past results untouched, and vice versa.
- `catalog.service` split in two along the line the slice already divides on: `service_authoring`
  writes an exam, `service` resolves one. Nine slices import `resolve_exam`, so the reading half
  kept the module name.
