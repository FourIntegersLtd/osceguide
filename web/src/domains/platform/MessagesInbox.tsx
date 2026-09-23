"use client";

import { useCallback, useState } from "react";
import { LuInbox } from "react-icons/lu";
import { AsyncBoundary, Badge, Button, Card } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { RowList } from "@/domains/platform/chrome";
import { listSiteMessages, markMessageHandled, type SiteMessage } from "@/domains/platform/api";
import { formatDay } from "@/domains/platform/support";

/**
 * The contact and feedback inbox.
 *
 * A person writes to us from the public contact form or the "Help us improve"
 * box inside the product, and `POST /site/messages` files it. Until this screen
 * existed, the filing was the end of the road: the queue was readable only with
 * a curl and an admin token, so a support note from a paying institution could
 * sit unanswered with nobody in the product able to see that it had arrived.
 *
 * The two kinds are separated because they have different readers and different
 * endings — a contact note wants a reply, a product suggestion wants triage — and
 * "Handled" is deliberately the only action. There is no reply-from-here: the
 * platform sends no outbound mail through this slice, and inventing a second
 * send path beside the support address would be a promise it cannot keep.
 */
export function MessagesInbox() {
  const [kind, setKind] = useState<"" | "contact" | "product_feedback">("");
  const [showHandled, setShowHandled] = useState(false);
  const state = useAsync((signal) => listSiteMessages({ kind }, signal), [kind]);

  const tabs: { id: "" | "contact" | "product_feedback"; label: string }[] = [
    { id: "", label: "All" },
    { id: "contact", label: "Contact" },
    { id: "product_feedback", label: "Product feedback" },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Messages"
        description="What people have written to the platform, and whether anybody has answered."
        icon={LuInbox}
      />

      <div className="flex flex-wrap items-center gap-2">
        {tabs.map((tab) => (
          <Button
            key={tab.id || "all"}
            size="sm"
            variant={kind === tab.id ? "primary" : "secondary"}
            onClick={() => setKind(tab.id)}
          >
            {tab.label}
          </Button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-sm text-ink-muted">
          <input
            type="checkbox"
            checked={showHandled}
            onChange={(event) => setShowHandled(event.target.checked)}
          />
          Show handled
        </label>
      </div>

      <AsyncBoundary
        state={state}
        isEmpty={(items) => items.length === 0}
        empty={{
          title: "Nothing waiting",
          description: "No messages of that kind have arrived.",
        }}
      >
        {(items) => (
          <RowList>
            {items
              .filter((message) => showHandled || !message.handled_at)
              .map((message) => (
                <MessageRow key={message.id} message={message} onReload={state.reload} />
              ))}
          </RowList>
        )}
      </AsyncBoundary>
    </div>
  );
}

function MessageRow({ message, onReload }: { message: SiteMessage; onReload: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await markMessageHandled(message.id);
      toast.success("Marked handled");
      onReload();
    } catch (cause) {
      // Stay in the queue. A row that says "handled" when the write failed is
      // how a message gets lost.
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [message.id, onReload, toast]);

  return (
    <Card
      title={message.subject ?? (message.kind === "contact" ? "Contact" : "Suggestion")}
      description={`${message.kind === "product_feedback" ? "Product feedback" : "Contact"} · ${
        message.name ?? message.email ?? "Anonymous"
      } · ${formatDay(message.created_at)}${message.source ? ` · ${message.source}` : ""}`}
      actions={
        message.handled_at ? (
          <Badge variant="neutral">Handled {formatDay(message.handled_at)}</Badge>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => void handle()} disabled={busy}>
            {busy ? "Saving…" : "Mark handled"}
          </Button>
        )
      }
    >
      <p className="whitespace-pre-wrap text-sm text-ink">{message.body}</p>
      {error ? (
        <p role="alert" className="mt-2 text-sm text-osce-danger">
          {error}
        </p>
      ) : null}
    </Card>
  );
}
