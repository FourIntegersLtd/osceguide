# 0001 — One app, shared capabilities, a surface per arm

**Status:** accepted · 2026-09-19

## Context

OSCE Guide sells to three kinds of customer: doctors practising for an exam,
institutions examining their trainees, and employers assessing candidates. The
retiring client, `frontend/`, has two source trees inside one Next app —
`src/b2c` (530 files) and `src/b2b` (466 files) — with `src/shared` (37 files)
between them.

That shape cost us the thing we most wanted. Every feature written for
consumers became consumer-only, one import at a time: the help section, the
slide decks, the A-to-Z summaries, the community. When institutions asked for
them, the answer was a port rather than a configuration change, and nothing in
the build caught the moment a shared thing stopped being shareable.

Meanwhile the backend never had arms at all. `platform-api` has exams,
organisations with programmes, entitlements, and **one `attempts` table** that
consumer practice, a mock station, a debrief, an exam slot and a peer session
all write to. A frontend that renders that one loop three times is fighting the
server it consumes.

## Decision

One app, five tiers, each importing only downwards:

```
  src/app          routes only — a page composes, it does not decide
  src/surfaces     one module per arm: train · assess · hire · partner · platform
  src/domains      arm-specific work
  src/capabilities mountable by ANY surface
  src/foundation   ui · session · platform-client · livekit · hooks · routing · charts
```

**The rule that carries the product requirement is the one on `capabilities`: a
capability may not import a surface or a domain.** A capability learns where it
is running only through `SurfaceContext`, which is deliberately two fields and
a href helper. Anything richer — the organisation's settings, the trainee's
cohort — would tempt a capability into branching on the arm, which is the
behaviour this tier exists to prevent.

`eslint-plugin-boundaries` fails the build on an upward import. Documentation
would not have held; the old client had the same intention written down.

## Consequences

Adding the study library to institutions was, in full:

1. `surfaces: ["train", "assess"]` in `src/capabilities/media/capability.ts`
2. a four-line route file

Navigation, the href prefix and the help assistant's knowledge of the section
all follow from the registry. `src/capabilities/registry.test.ts` pins it, so
narrowing it back to consumers fails a test rather than quietly removing a
section from a customer.

An arm is a *skin and a nav over shared machinery*, not a product. Hire is
literally the Assess surface module with different wording
(`{ ...assessSurface, id: "hire" }`). When that stops being true for a real
employer, Hire gets its own `screens` entries — and still no second
implementation of a sitting.

## Alternatives rejected

**Three apps.** Honest about the arms, dishonest about the backend. One
`attempts` table rendered by three codebases means three attempt runners, three
feedback renderers and three LiveKit integrations to keep in step.

**A shared package plus two apps.** What `frontend/` already is. The shared
package is where things go to become unshared, because nothing stops an app
from reaching past it.
