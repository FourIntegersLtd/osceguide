# 0014. Social content is addressed to an audience, not just an exam

Date: 2026-09-17
Status: accepted

## Context
`community`, `marketplace` and `peer_practice` each hold something one person offers to
others: a question, a practice slot, a place in a matching queue. All three were addressed to
an exam and nothing else, so each was a single global pool. An institution's trainees had no
way to talk among themselves, a teaching group had no way to practise together, and a
supervisor could not put one circuit's candidates in a room of their own.

The obvious fix is to let those slices read cohorts and trainee groups from `roster`. The
layer order forbids it: `roster` sits above all three, and lowering it would answer the cohort
case while leaving the "same session" case needing `sittings`, which sits higher still and
drags `stations` and feedback templates behind it. Pulling a large dependency downward to
answer a visibility question is the wrong shape, and it would have to be done again the next
way of grouping people that appears.

## Decision
An **audience** is its own concept, in the shared kernel: a visibility (`public`,
`organisation`, `group`), an organisation, and one group id. The three slices store it, filter
on it, and never learn what a group *is*.

Who a given viewer belongs to is a single lookup bound in `main.py`, the seam
`bind_membership_lookup` and `bind_purchase_counter` already use. `roster` implements it,
composing organisation memberships with teaching groups.

A group audience must name its organisation as well as its group, so that moderation has one
rule to read.

## Consequences
- All three groupings work with no change to the layer order. Same institution is the
  organisation; same cohort or teaching group is a group; **same session needs no new
  dependency at all** — whoever schedules a sitting mints a group holding that circuit's
  trainees and points the audience at it. A study group somebody forms themselves is the same
  mechanism later.
- Exam stays orthogonal. "PLAB candidates in my cohort" is a filter combination rather than a
  new concept, and the existing global pools are `public`, which is what they already were.
- The filter is one function in core rather than three hand-written copies. Keyset paging was
  copied into nine repositories and nine of them dropped rows; this one decides who can read an
  institution's private conversation, so a copy that omits a clause is worse.
- A CHECK constraint refuses a row naming a visibility and then nobody. Without it such a row
  reads as public to the filter and publishes a conversation its author believed was private.
- Matching and queue position become per room. Pairing an exam as one pool would put a trainee
  waiting inside their institution with a stranger.
- One queue place per person per exam still holds across rooms, so nobody waits in two at once.
- An institution's admins may remove anything addressed inside their institution. Content stays
  when its author leaves: a group would otherwise lose half a conversation when one person goes.
- Revoked trainees stop seeing an institution's rooms, because the lookup excludes them.
