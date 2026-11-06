"use client";

import { b2bTokens } from "@/foundation/ui";

/**
 * The chrome the team and the roster share.
 *
 * They were one screen in the retiring client — `/team` held a Members tab
 * with both staff and trainees on it — and they are two screens here. What
 * they still have in common is this: the tab strip under the page title and the
 * grouped card. It lives with Team because that is where
 * `TeamPageHeaderNav` and `TeamPageCard` came from.
 */

export interface Tab<T extends string> {
  key: T;
  label: string;
  /** A count shown beside the label, in grey. */
  count?: number;
}

/**
 * The segmented control under the page title.
 *
 * `/team`, `/team/activity` and `/team/onboard` were separate pages whose
 * every visit refetched the same two lists. There is one route per screen in
 * this client, so the sections are state, which also means switching tabs no
 * longer loses a half-typed invitation.
 */
export function TabStrip<T extends string>({
  tabs,
  active,
  onSelect,
  label,
}: {
  tabs: readonly Tab<T>[];
  active: T;
  onSelect: (key: T) => void;
  label: string;
}) {
  return (
    <div className={b2bTokens.b2bSegmentedControl} role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={active === tab.key}
          onClick={() => onSelect(tab.key)}
          className={
            active === tab.key ? b2bTokens.b2bSegmentedTabActive : b2bTokens.b2bSegmentedTabInactive
          }
        >
          {tab.label}
          {tab.count !== undefined ? (
            <span className="text-osce-meta text-b2b-mid">{tab.count}</span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

/** "3 Sept 2026, 14:20" — the audit log's stamp, and the entitlement's. */
export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "None";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
