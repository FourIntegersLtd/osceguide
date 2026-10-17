"use client";

import { Suspense, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  AsyncBoundary,
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  B2CPageHeader,
} from "@/foundation/ui";
import { useCursorPages } from "@/foundation/hooks";
import { listPlatformAudit } from "@/domains/platform/support/api";
import { AuditTable } from "@/domains/platform/user/HistoryTab";

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
  const pages = useCursorPages(
    (cursor, signal) => listPlatformAudit({ orgSlug, actorEmail, action, limit: 100, cursor }, signal),
    [orgSlug, actorEmail, action],
  );
  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Audit log"
        subtitle="Who changed what, across the platform."
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
      <AsyncBoundary state={pages.state}>
        {(items) => (
          <AuditTable
            rows={items}
            more={pages}
            empty={{ title: "Nothing recorded", description: "No rows match." }}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}
