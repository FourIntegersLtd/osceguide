"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { b2bTokens as t, cn, LeaveConfirmModal } from "@/foundation/ui";
import { Chip, Note } from "@/domains/assess/ui";
import { SettingsCard } from "@/domains/assess/settings/SettingsCard";
import { useAsync, useLeaveGuard } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOrganization } from "@/domains/assess/api";
import { InvoiceBrowser } from "@/domains/assess/settings/InvoicesPanel";
import { boardBtn } from "@/foundation/ui/boardKit";

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
    <SettingsCard
      title="Invoices"
      lead={`Invoices OSCE Guide raises for ${name}, and the purchase order number your finance team needs on them.`}
    >
      <div className="flex flex-col items-start gap-4">
        <Link href={hrefFor("/settings/invoices")} className={boardBtn("primary")}>
          Open invoices
        </Link>
        <Chip tone="info">New</Chip>
      </div>
    </SettingsCard>
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
    return <Note tone="info">Invoices are for your organisation&apos;s administrators.</Note>;
  }
  return (
    <div className="flex min-w-0 flex-col gap-6">
      <div>
        <Link href={settings} className="text-assess-label">
          ‹ Settings
        </Link>
      </div>
      <div>
        <div className={t.assessEyebrow}>Settings</div>
        <h1 className={t.assessTitle}>Invoices</h1>
        <p className={cn(t.assessDesc, "m-0")}>{`Raised by OSCE Guide for ${name}.`}</p>
      </div>
      <InvoiceBrowser orgSlug={orgSlug} setDirty={setDirty} />
      <LeaveConfirmModal
        isOpen={guard.asking}
        onStay={guard.stay}
        onLeave={() => {
          const href = guard.confirmLeave();
          if (href) router.push(href);
        }}
      />
    </div>
  );
}
