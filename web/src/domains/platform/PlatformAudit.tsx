"use client";

import { Suspense, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
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

/**
 * The three audit filters, kept in the address (`?org=&actor=&action=`) so a
 * reload or a copied link shows the same view. The inputs keep their own state
 * so typing never waits on the router; the address follows.
 */
function useAuditFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [values, setValues] = useState({
    org: searchParams.get("org") ?? "",
    actor: searchParams.get("actor") ?? "",
    action: searchParams.get("action") ?? "",
  });
  const set = (key: keyof typeof values) => (value: string) => {
    const next = { ...values, [key]: value };
    setValues(next);
    const params = new URLSearchParams();
    for (const [name, text] of Object.entries(next)) if (text) params.set(name, text);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };
  return {
    orgSlug: values.org,
    actorEmail: values.actor,
    action: values.action,
    setOrgSlug: set("org"),
    setActorEmail: set("actor"),
    setAction: set("action"),
  };
}

/** Who changed what, across every organisation and the platform itself. */
export function PlatformAudit() {
  // `useSearchParams` needs a boundary in the app router.
  return (
    <Suspense fallback={null}>
      <AuditLog />
    </Suspense>
  );
}

function AuditLog() {
  const { orgSlug, actorEmail, action, setOrgSlug, setActorEmail, setAction } = useAuditFilters();
  const state = useAsync(
    (signal) =>
      listPlatformAudit({ orgSlug, actorEmail, action, limit: 100 }, signal),
    [orgSlug, actorEmail, action],
  );
  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Audit log"
        description="Who changed what, across the platform."
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
          placeholder="Action, such as access"
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
