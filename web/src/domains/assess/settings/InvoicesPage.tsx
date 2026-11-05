"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LuChevronRight } from "react-icons/lu";
import { Alert, B2CPageHeader, Badge, LeaveConfirmModal, Panel } from "@/foundation/ui";
import { useAsync, useLeaveGuard } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOrganization } from "@/domains/assess/api";
import { InvoiceBrowser } from "@/domains/assess/settings/InvoicesPanel";

/** The organisation's name for the invoice copy, "your organisation" until it loads. */
function useOrgName(orgSlug: string): string {
  const org = useAsync((signal) => readOrganization(orgSlug, signal), [orgSlug]);
  return org.data?.name ?? "your organisation";
}

/** The Settings "Invoices" tab: what the page is for, and the way into it. */
export function InvoicesTab({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const name = useOrgName(orgSlug);
  return (
    <Panel
      title="Invoices"
      description={`Invoices OSCE Guide raises for ${name}, and the purchase order number your finance team needs on them.`}
    >
      <Link
        href={hrefFor("/settings/invoices")}
        className="flex items-center justify-between gap-3 rounded-control border border-border bg-surface px-4 py-3 text-osce-body font-medium text-ink hover:bg-canvas"
      >
        <span className="flex items-center gap-2">
          Open invoices
          <Badge variant="info">New</Badge>
        </span>
        <LuChevronRight aria-hidden className="h-4 w-4 text-ink-muted" />
      </Link>
    </Panel>
  );
}

/** `/settings/invoices`: the list and one invoice, for an organisation's admin. */
export function InvoicesPage() {
  const { orgSlug, hrefFor } = useSurface();
  const { session } = useSession();
  const router = useRouter();
  const name = useOrgName(orgSlug ?? "");
  const [dirty, setDirty] = useState(false);
  const guard = useLeaveGuard(dirty);
  const settings = hrefFor("/settings?tab=invoices");

  const isAdmin = can(session, "manage_team");

  if (!orgSlug || !isAdmin) {
    return <Alert tone="info">Invoices are for your organisation&apos;s administrators.</Alert>;
  }
  return (
    <>
      <B2CPageHeader
        back={{ href: settings, label: "Settings" }}
        title="Invoices"
        subtitle={`Raised by OSCE Guide for ${name}.`}
      />
      <InvoiceBrowser orgSlug={orgSlug} setDirty={setDirty} />
      <LeaveConfirmModal
        isOpen={guard.asking}
        onStay={guard.stay}
        onLeave={() => {
          const href = guard.confirmLeave();
          if (href) router.push(href);
        }}
      />
    </>
  );
}
