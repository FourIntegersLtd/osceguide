# 0002 — Workspace-first URLs

**Status:** accepted · 2026-09-19 · supersedes an unwritten "consumer at root" habit

## Context

The first cut of `platform-web` put the consumer arm in a Next route group,
`src/app/(train)/`. A route group is invisible in the URL, so those pages sat
at the site root — `/mocks`, `/library`, `/practice` — while institutions were
at `/assess/<slug>` and employers at `/hire/<slug>`.

Nobody had written that down, so it read as an accident. It also produced two
real defects:

- Signing in as an org member always landed on the institution arm, because the
  front door branched on memberships and only a membership-less account could
  reach the consumer screens.
- There was no way to move between "my own practice" and "my institution"
  inside the app at all.

## Decision

Marketing owns the root. Every signed-in screen lives under one grammar:

```
osceguide.com/                      landing, /exams/[exam], /institutions, /pricing, /blogs, /compliances/*
osceguide.com/login  /register      auth
osceguide.com/app                   → the last-used workspace, else /app/me
osceguide.com/app/me/…              personal practice
osceguide.com/app/<orgSlug>/…       an organisation
osceguide.com/staff/…               the OSCE Guide console
```

**A person's own practice is a workspace, addressed exactly like an
organisation's.** The shell is chosen by the workspace's `org_type` —
`institution → Assess`, `partner → Partner`, `employer → Hire`, personal →
Train — never by a URL prefix.

This is the shape of every product with a personal space and a team space:
GitHub `/<owner>`, Linear `/<workspace>`, Vercel `/<team>` (the personal
account is a team called Hobby), Notion `/<workspace>`.

## Consequences

- **One rule decides the shell.** Adding an arm is a new `org_type` mapped to a
  surface module. No new URL prefix, no new route tree, no new redirect.
- **The switcher is natural.** "My practice" and "King's" are two entries in
  one list.
- **Marketing keeps the root and the SEO.** App pages are behind auth and have
  none to lose.
- **A subdomain later is a rewrite rule.** `/app/*` becomes
  `app.osceguide.com/*` with no code change. Starting on a path avoids cookie
  and CORS work in local development.
- **`me` is a reserved slug.** No organisation may take it;
  `foundation/routing` owns that list.
- **Old links break.** `foundation/routing/legacyRedirects.ts` maps every
  retiring path (`/mocks`, `/dashboard`, `/b2b/<org>/sessions`, …) to its new
  address, applied in `middleware.ts` and covered by a test.

## Why not the alternatives

**Consumer at the root.** What we had. It is the shape of a product with one
audience, and it forces a special case into every routing decision the moment
there is a second.

**Everything under `/platform`.** "Platform" is already the staff console and
the name of the backend. If everything shares one prefix, that prefix is `app`.

**A subdomain per arm now.** Cookie domains, CORS and three dev servers, bought
before we know we need it. The path form upgrades into it later.
