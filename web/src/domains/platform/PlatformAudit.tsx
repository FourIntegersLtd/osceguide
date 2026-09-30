"use client";

import { useState } from "react";
import { LuScrollText } from "react-icons/lu";
import {
  AsyncBoundary,
  Panel,
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  PlatformPageHeader,
  RowList,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listPlatformAudit } from "@/domains/platform/support/api";
import { PlatformAuditRow } from "@/domains/platform/user/HistoryTab";

/** Who changed what, across every organisation and the platform itself. */
export function PlatformAudit() {
  const [orgSlug, setOrgSlug] = useState("");
  const [actorEmail, setActorEmail] = useState("");
  const [action, setAction] = useState("");
  const state = useAsync(
    (signal) =>
      listPlatformAudit({ orgSlug, actorEmail, action, limit: 100 }, signal),
    [orgSlug, actorEmail, action],
  );
  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Audit log"
        description="Every organisation's log, and the platform's own rows."
        icon={LuScrollText}
      />
      <PlatformFilterBar>
        <PlatformFilterSearch
          value={orgSlug}
          onChange={setOrgSlug}
          placeholder="Organisation slug"
        />
        <PlatformFilterDivider />
        <PlatformFilterSearch
          value={actorEmail}
          onChange={setActorEmail}
          placeholder="Actor email"
        />
        <PlatformFilterDivider />
        <PlatformFilterSearch
          value={action}
          onChange={setAction}
          placeholder="Action, e.g. entitlement"
          aria-label="Action name or prefix"
        />
      </PlatformFilterBar>
      <Panel padding="none">
        <AsyncBoundary
          state={state}
          isEmpty={(page) => page.items.length === 0}
          empty={{
            title: "Nothing recorded",
            description: "No rows match.",
            bare: true,
          }}
        >
          {(page) => (
            <RowList flush>
              {page.items.map((entry) => (
                <PlatformAuditRow key={entry.id} entry={entry} />
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Panel>
    </div>
  );
}
