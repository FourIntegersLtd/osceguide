# inbox

## Purpose
In-app messages to a person: the answer to a station report, a reply to something
they wrote to us, a note from staff, and announcements to everybody. In-app only;
email goes through `notifications.enqueue_email` when it is wanted.

## Aggregates & invariants
**UserMessage** and **UserMessageRead**.

- `service.deliver` is the single write path. Each message writes an audit row (so it
  shows in the user's History) and publishes `message.received` on the recipient's
  `/me/events` topic after the commit.
- An announcement has no recipient and nothing else lacks one (`ck_user_messages_audience`).
  It is never fanned out into a row per user: a read row exists only once somebody reads it.
- An announcement reaches accounts that existed when it was posted
  (`created_at >= users.created_at`), so a new sign-up does not inherit history.
  Withdrawn announcements disappear from every inbox.
- The learner always sees "OSCE Guide team", never the staff member's name.
- Erasure deletes messages addressed to the person; announcements stay.

## Routes
| Route | Who |
|---|---|
| `GET /me/messages`, `GET /me/messages/unread-count` | Signed in |
| `POST /me/messages/{id}/read`, `POST /me/messages/read-all` | Signed in |
| `POST /platform/users/{id}/messages` | Platform admin |
| `GET`, `POST /platform/announcements`, `POST /platform/announcements/{id}/withdraw` | Platform admin |

## Jobs
None.

## Cross-slice dependencies
`identity` (account age, names, `UserNotFound`), `tenancy.service_audit` (the audit row),
`core.events`. Called by `stations` (answer to a report) and `public_site` (reply to a
message); `identity.service_erasure` calls `erase_for_user`.
