"use client";

import { useState } from "react";
import { LuShieldCheck } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  Badge,
  Button,
  B2CSegmentedTabs,
  B2CPageHeader,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readDirectoryUser, readUser, type PlatformUserDetail } from "@/domains/platform/api";
import { formatDay } from "@/domains/platform/support";
import { accessLabel, accessOf, accessTone, userStatusTone } from "@/domains/platform/users/vocabulary";
import { SendMessageModal } from "@/domains/platform/user/SendMessageModal";
import { AccountTab } from "@/domains/platform/user/AccountTab";
import { AttemptsTab } from "@/domains/platform/user/AttemptsTab";
import { BillingTab } from "@/domains/platform/user/BillingTab";
import { EntitlementsTab } from "@/domains/platform/user/EntitlementsTab";
import { HistoryTab } from "@/domains/platform/user/HistoryTab";
import { ProfileTab } from "@/domains/platform/user/ProfileTab";
import { StationsTab } from "@/domains/platform/user/StationsTab";

type Tab = "profile" | "stations" | "attempts" | "entitlements" | "billing" | "account" | "history";

/**
 * The support view of one account — the retiring B2C admin's user detail.
 *
 * Profile is who they are; Account is what they paid for, where they belong
 * and the two switches. Stations, Attempts, Entitlements, Billing and History
 * answer the tickets support actually gets, and carry the levers.
 */
const USER_TABS: B2CSegmentedTabItem<Tab>[] = [
  { id: "profile", label: "Profile" },
  { id: "stations", label: "Stations" },
  { id: "attempts", label: "Attempts" },
  { id: "entitlements", label: "Access" },
  { id: "billing", label: "Billing" },
  { id: "account", label: "Account" },
  { id: "history", label: "History" },
];

export function UserDetail({ userId }: { userId: string }) {
  const { hrefFor } = useSurface();
  const [tab, setTab] = useState<Tab>("profile");
  const state = useAsync((signal) => readUser(userId, signal), [userId]);
  // The directory's row: paid, plan, live access, signed in. Its own load so a
  // hiccup in one of four slices does not take the profile down with it.
  const facts = useAsync((signal) => readDirectoryUser(userId, signal), [userId]);
  const [messaging, setMessaging] = useState(false);
  // Bumped after a message is sent, so History is re-read and shows the audit row.
  const [historyKey, setHistoryKey] = useState(0);
  const [fresh, setFresh] = useState<PlatformUserDetail | null>(null);
  const user = fresh ?? state.data;

  const changed = (next: PlatformUserDetail) => {
    setFresh(next);
    facts.reload();
  };

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(loaded) => {
          const current = user ?? loaded;
          const access = facts.data ? accessOf(facts.data) : null;
          return (
            <>
              <B2CPageHeader
                title={current.email}
                subtitle={`${current.name || "No name"} · joined ${formatDay(current.created_at)}${
                  current.exam_code
                    ? ` · ${current.exam_code.toUpperCase()}`
                    : ""
                }`}
                back={{ href: hrefFor("/users"), label: "Users" }}
                action={
                  <span className="flex flex-wrap items-center gap-1.5">
                    <Button variant="secondary" size="sm" onClick={() => setMessaging(true)}>
                      Send message
                    </Button>
                    <Badge tone={userStatusTone(current.status)}>
                      {current.status === "deactivated" ? "Deactivated" : "Active"}
                    </Badge>
                    {facts.data ? (
                      <Badge tone={facts.data.signed_in ? "success" : "neutral"}>
                        {facts.data.signed_in ? "Session open" : "No open session"}
                      </Badge>
                    ) : null}
                    {access ? (
                      <Badge tone={accessTone(access)}>{accessLabel(access)}</Badge>
                    ) : null}
                    {current.is_platform_admin ? (
                      <Badge tone="accent">
                        <LuShieldCheck className="mr-1 h-3 w-3" aria-hidden />
                        Console
                      </Badge>
                    ) : null}
                  </span>
                }
              />

              {facts.error ? (
                <Alert tone="danger">
                  Could not load their payment and access details: {errorMessage(facts.error)}. The Account tab will
                  show them as unknown, not as none.
                </Alert>
              ) : null}

              <B2CSegmentedTabs items={USER_TABS} value={tab} onChange={setTab} aria-label="User detail" className="mb-0 sm:mb-0" />

              {tab === "profile" ? (
                <ProfileTab user={current} onSaved={changed} />
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
              {tab === "history" ? <HistoryTab key={historyKey} userId={current.id} /> : null}
              {messaging ? (
                <SendMessageModal
                  userId={current.id}
                  onClose={() => setMessaging(false)}
                  onSent={() => setHistoryKey((key) => key + 1)}
                />
              ) : null}
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
