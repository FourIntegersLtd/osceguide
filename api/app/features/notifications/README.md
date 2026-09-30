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
  six attempts rather than retried forever — a queue that never gives up hides
  the fact that something needs a person.
- Each message is attempted independently: one bad address does not stop the queue.

## Routes
None. This slice is queue and worker only; nothing outside asks it for anything
over HTTP.

## Jobs
`deliver_outbound_messages` — periodic, every minute.

## Cross-slice dependencies
None. Other slices call `enqueue_email`. The provider sits behind
`core.ports.EmailSender`, so the queue's behaviour is testable with a fake and
no Resend account.
