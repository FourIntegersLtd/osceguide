"use client";

import { useState } from "react";
import { LuScrollText } from "react-icons/lu";
import { AsyncBoundary, Input } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { listPlatformAudit } from "@/domains/platform/support/api";
import { RowList } from "@/domains/platform/chrome";
import { PlatformAuditRow } from "@/domains/platform/user/HistoryTab";

/** Who changed what, across every organisation and the platform itself. */
export function PlatformAudit() {
  const [orgSlug, setOrgSlug] = useState("");
  const [actorEmail, setActorEmail] = useState("");
  const [action, setAction] = useState("");
  const state = useAsync(
    (signal) => listPlatformAudit({ orgSlug, actorEmail, action, limit: 100 }, signal),
    [orgSlug, actorEmail, action],
  );
  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader title="Audit log" description="Every organisation's log, and the platform's own rows." icon={LuScrollText} />
      <div className="grid gap-3 sm:grid-cols-3">
        <Input label="Organisation slug" value={orgSlug} onChange={(e) => setOrgSlug(e.target.value)} />
        <Input label="Actor email" value={actorEmail} onChange={(e) => setActorEmail(e.target.value)} />
        <Input label="Action" value={action} onChange={(e) => setAction(e.target.value)} hint="A name or prefix, e.g. entitlement." />
      </div>
      <AsyncBoundary state={state} isEmpty={(p) => p.items.length === 0} empty={{ title: "Nothing recorded", description: "No rows match." }}>
        {(page) => (
          <RowList>
            {page.items.map((entry) => (
              <PlatformAuditRow key={entry.id} entry={entry} />
            ))}
          </RowList>
        )}
      </AsyncBoundary>
    </div>
  );
}
