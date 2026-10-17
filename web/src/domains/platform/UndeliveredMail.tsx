"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Button } from "@/foundation/ui";
import Table from "@/foundation/table/Table";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { listUndeliveredMail, retryUndeliveredMail, type UndeliveredMessage } from "@/domains/platform/support/api";
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
    <div className="flex flex-col gap-4">
      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      <AsyncBoundary state={mail}>
        {({ messages, has_more }) => (
          <>
            <Table<UndeliveredMessage>
              rows={messages}
              themeType="b2b"
              idField="id"
              title="Undelivered email"
              description="Email the provider refused for about five hours of tries. Retry sends it again from the start once the provider is back."
              empty={{ title: "Nothing undelivered", description: "Every email went out." }}
              columns={[
                {
                  header: "Email",
                  key: "subject",
                  priority: "primary",
                  render: (message) => (
                    <div className="min-w-0">
                      <p className="font-medium text-ink">
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
                  ),
                },
                {
                  header: "",
                  key: "id",
                  render: (message) => (
                    <Button
                      themeType="b2b"
                      variant="secondary"
                      size="sm"
                      isLoading={retrying === message.id}
                      disabled={retrying !== null}
                      onClick={() => retry(message.id)}
                    >
                      Retry
                    </Button>
                  ),
                },
              ]}
            />
            {has_more ? (
              <p className="text-osce-meta text-ink-subtle">
                Showing the newest {messages.length}. Retry these and the older ones appear here.
              </p>
            ) : null}
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
