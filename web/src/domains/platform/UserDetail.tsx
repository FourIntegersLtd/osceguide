"use client";

import Link from "next/link";
import { useState } from "react";
import { LuShieldCheck } from "react-icons/lu";
import { AsyncBoundary, Badge, B2CSegmentedTabs, Card, type B2CSegmentedTabItem } from "@/foundation/ui";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readDirectoryUser, readUser, type PlatformUserDetail } from "@/domains/platform/api";
import { Row, RowList } from "@/domains/platform/chrome";
import { formatDay } from "@/domains/platform/support";
import { accessLabel, accessOf, accessTone, userStatusTone } from "@/domains/platform/users/vocabulary";
import { AccountTab } from "@/domains/platform/user/AccountTab";
import { AttemptsTab } from "@/domains/platform/user/AttemptsTab";
import { BillingTab } from "@/domains/platform/user/BillingTab";
import { EntitlementsTab } from "@/domains/platform/user/EntitlementsTab";
import { HistoryTab } from "@/domains/platform/user/HistoryTab";
import { B2cUserOverview } from "@/domains/platform/user/B2cUserOverview";
import { StationsTab } from "@/domains/platform/user/StationsTab";

type Tab = "profile" | "stations" | "attempts" | "entitlements" | "billing" | "account" | "memberships" | "history";

/**
 * The support view of one account — the retiring B2C admin's user detail.
 *
 * Profile and Stations are that screen's two cards; Account is its status
 * card, read from facts rather than flags. Attempts, Entitlements, Billing and
 * History answer the tickets support actually gets, and carry the levers.
 */
const USER_TABS: B2CSegmentedTabItem<Tab>[] = [
  { id: "profile", label: "Profile" },
  { id: "stations", label: "Stations" },
  { id: "attempts", label: "Attempts" },
  { id: "entitlements", label: "Entitlements" },
  { id: "billing", label: "Billing" },
  { id: "account", label: "Account" },
  { id: "memberships", label: "Memberships" },
  { id: "history", label: "History" },
];

export function UserDetail({ userId }: { userId: string }) {
  const { hrefFor } = useSurface();
  const [tab, setTab] = useState<Tab>("profile");
  const state = useAsync((signal) => readUser(userId, signal), [userId]);
  // The directory's row: paid, plan, live access, signed in. Its own load so a
  // hiccup in one of four slices does not take the profile down with it.
  const facts = useAsync((signal) => readDirectoryUser(userId, signal), [userId]);
  const [fresh, setFresh] = useState<PlatformUserDetail | null>(null);
  const user = fresh ?? state.data;

  const changed = (next: PlatformUserDetail) => {
    setFresh(next);
    facts.reload();
  };

  return (
    <div className="flex flex-col gap-4">
      <Link
        href={hrefFor("/users")}
        className="inline-flex items-center gap-1 rounded-md text-osce-meta font-medium text-b2c-text-muted hover:text-osce-ink-900 focus:outline-none focus:ring-2 focus:ring-osce-accent/20"
      >
        ← Users
      </Link>

      <AsyncBoundary state={state}>
        {(loaded) => {
          const current = user ?? loaded;
          const access = facts.data ? accessOf(facts.data) : null;
          return (
            <>
              <PlatformPageHeader
                title={current.email}
                description={`${current.name || "No name"} · joined ${formatDay(current.created_at)}${
                  current.exam_code ? ` · ${current.exam_code.toUpperCase()}` : ""
                }`}
                actions={
                  <span className="flex flex-wrap items-center gap-1.5">
                    <Badge tone={userStatusTone(current.status)}>
                      {current.status === "deactivated" ? "Deactivated" : "Active"}
                    </Badge>
                    {facts.data ? (
                      <Badge tone={facts.data.signed_in ? "success" : "neutral"}>
                        {facts.data.signed_in ? "Signed in" : "Signed out"}
                      </Badge>
                    ) : null}
                    {access ? <Badge tone={accessTone(access)}>{accessLabel(access)}</Badge> : null}
                    {current.is_platform_admin ? (
                      <Badge tone="accent">
                        <LuShieldCheck className="mr-1 h-3 w-3" aria-hidden />
                        Console
                      </Badge>
                    ) : null}
                  </span>
                }
              />

              <B2CSegmentedTabs items={USER_TABS} value={tab} onChange={setTab} aria-label="User detail" />

              {tab === "profile" ? (
                <B2cUserOverview user={current} facts={facts.data} onSaved={changed} />
              ) : null}
              {tab === "stations" ? <StationsTab userId={current.id} /> : null}
              {tab === "attempts" ? <AttemptsTab userId={current.id} /> : null}
              {tab === "entitlements" ? (
                <EntitlementsTab userId={current.id} examCode={current.exam_code} />
              ) : null}
              {tab === "billing" ? <BillingTab userId={current.id} /> : null}
              {tab === "account" ? (
                <AccountTab user={current} facts={facts.data} onChanged={changed} onOpenTab={setTab} />
              ) : null}
              {tab === "memberships" ? <MembershipsTab user={current} /> : null}
              {tab === "history" ? <HistoryTab userId={current.id} /> : null}
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function MembershipsTab({ user }: { user: PlatformUserDetail }) {
  const memberships = user.memberships ?? [];

  return memberships.length === 0 ? (
    <Card padding="md">
      <p className="text-osce-body text-b2c-text-muted">This account belongs to no organisation.</p>
    </Card>
  ) : (
    <RowList>
      {memberships.map((membership) => (
        <Row key={membership.id}>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{membership.email ?? membership.user_id}</p>
            <p className="truncate text-xs text-ink-subtle">{membership.role}</p>
          </div>
        </Row>
      ))}
    </RowList>
  );
}
