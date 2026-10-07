"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Button, Panel, Row, RowList } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { listUndeliveredMail, retryUndeliveredMail } from "@/domains/platform/support/api";
import { formatMoment } from "@/domains/platform/support";

/** Email the outbox gave up on, each with the reason and a retry, on System health. */
export function UndeliveredMail() {
  const mail = useAsync((signal) => listUndeliveredMail(signal), []);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const retry = async (messageId: string) => {
    setRetrying(messageId);
    setFailure(null);
    try {
      await retryUndeliveredMail(messageId);
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setRetrying(null);
      mail.reload();
    }
  };

  return (
    <Panel
      title="Undelivered email"
      description="Email the provider refused for about five hours of tries. Retry sends it again from the start once the provider is back."
      padding="none"
    >
      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      <AsyncBoundary
        state={mail}
        isEmpty={(page) => page.messages.length === 0}
        empty={{ title: "Nothing undelivered", description: "Every email went out.", bare: true }}
      >
        {({ messages, has_more }) => (
          <>
          <RowList flush>
            {messages.map((message) => (
              <Row key={message.id}>
                <div className="min-w-0">
                  <p className="text-osce-data font-medium text-ink">
                    {message.subject} · {message.recipient}
                  </p>
                  <p className="truncate text-osce-meta text-ink-subtle">
                    {[
                      `Gave up ${formatMoment(message.abandoned_at)} after ${message.attempts} tries`,
                      message.last_error,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  isLoading={retrying === message.id}
                  disabled={retrying !== null}
                  onClick={() => retry(message.id)}
                >
                  Retry
                </Button>
              </Row>
            ))}
          </RowList>
          {has_more ? (
            <p className="px-4 py-3 text-osce-meta text-ink-subtle">
              Showing the newest {messages.length}. Retry these and the older ones appear here.
            </p>
          ) : null}
          </>
        )}
      </AsyncBoundary>
    </Panel>
  );
}
