# public_site

## Purpose

What the marketing site needs from the backend, and what an anonymous visitor
may send us.

Two unrelated things with the same caller — nobody is signed in — which is the
whole reason they share a slice: the threat model is the same and it is the
only thing about them that is interesting.

## Aggregates & invariants

**SiteMessage** is the only table. The statistics have none: they are counted
from the slices that own the rows.

- **A contact message needs a reply address; product feedback does not.**
  Somebody telling us a button is confusing should not have to identify
  themselves. Somebody asking a question has to be answerable.
- **Kinds are separate because they are read by different people.** Contact
  wants answering; feedback wants collating.
- **The statistics are cached for ten minutes.** The landing page is the
  busiest thing on the site, and `as_of` is returned so a client can say when
  they were counted rather than implying they are live.
- **A signed-in sender is recorded, an anonymous one is not chased.** A null
  `user_id` says nothing about whether they have an account.

## Routes

| Route | Who |
|---|---|
| `GET /site/statistics` | Anyone, unauthenticated |
| `POST /site/messages` | Anyone; rate-limited per caller |
| `GET /platform/site/messages` | Platform admin |
| `POST /platform/site/messages/{id}/handled` | Platform admin |
| `POST /platform/site/messages/{id}/reply` | Platform admin; answers into the sender's inbox, 409 `message_not_repliable` when they were not signed in |

## Jobs

None. Nothing here sends an email: a message is stored and read from the
console. Notifying somebody that a message arrived belongs to `notifications`
when that grows a channel for it.

## Cross-slice dependencies

Through services only. `inbox` (a reply is delivered there). To count: `attempts` (consultations and
debriefs), `identity` (users), `stations` (the platform catalogue). This slice
reads no table but its own.
