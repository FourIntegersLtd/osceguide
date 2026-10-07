# notifications

## Purpose
One outbox for everything the platform sends. Slices queue a message in the
transaction that justified it; a worker drains the queue.

## Use cases
- As the **platform**, I queue a password-reset email beside the token that
  makes it valid, so neither exists without the other.
- As the **platform**, I tell a candidate their result has been released.
- As **support**, I can see what is stuck and why.

## Aggregates & invariants
**OutboundMessage** stands alone.

- Queueing happens in the caller's transaction. A password reset that rolls back
  does not leave an email promising one.
- Every message carries an idempotency key from the slice that wrote it. A
  repeat is a no-op, not a second email.
- Delivery claims rows with `FOR UPDATE SKIP LOCKED`, so two workers never send
  the same message and neither waits on the other.
- Failures back off exponentially, capped at an hour, and are **abandoned** after
  twelve attempts (about five hours) rather than retried forever — a queue that
  never gives up hides the fact that something needs a person. Six attempts
  gave up after fifteen minutes, so one provider outage lost every invitation
  and reset queued during it.
- An abandoned message is logged as an error (Sentry) and stays `failed`; the
  console's System health page lists it and can queue it again with fresh
  attempts (`list_undelivered`, `retry_undelivered`, served by `health`).
- Each message is attempted independently: one bad address does not stop the queue.

## Routes
None of its own. The console's undelivered-mail list and retry are served by
`health` (`/platform/outbox/...`), which calls this slice's service and owns
the `message_not_retryable` refusal (`retry_undelivered` answers a bool).

## Jobs
`deliver_outbound_messages` — periodic, every minute.

## Cross-slice dependencies
None. Other slices call `enqueue_email`. The provider sits behind
`core.ports.EmailSender`, so the queue's behaviour is testable with a fake and
no Resend account.
