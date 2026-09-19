"use client";

import { useState } from "react";
import { LuUserCog } from "react-icons/lu";
import { HiOutlineIdentification, HiOutlineKey } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  Modal,
  ModalHelper,
  ModalSecondaryButton,
  productTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { readMe, type Me } from "@/capabilities/account/api";
import ChangePassword from "@/capabilities/account/settings/ChangePassword";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const {
  b2cFieldLabel,
  b2cSettingsCardHeaderIcon,
  b2cSettingsFieldInputDisabled,
} = productTokens;

/**
 * Who you are, and the one thing about it you can change today.
 *
 * The name and the address are read back rather than edited: `platform-api`
 * has no write on `/me`, and a box that discards what you typed is worse than
 * a box you cannot type in. The old client's editable username, its account
 * deletion and its CV upload are in `docs/port-gaps.md` with the endpoints
 * each would need.
 */
export default function ProfilePanel() {
  const me = useAsync((signal) => readMe(signal), []);
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);

  return (
    <SettingsTabShell>
      <AsyncBoundary state={me}>
        {(user: Me) => (
          <B2CPanelCard className="mt-0">
            <B2CPanelCardHeader>
              <LuUserCog className={b2cSettingsCardHeaderIcon} aria-hidden />
              Account
            </B2CPanelCardHeader>
            <B2CPanelCardBody className="space-y-4">
              <ModalHelper className="mt-0">
                Your sign-in details and account actions.
              </ModalHelper>

              <div>
                <label htmlFor="profile-name" className={b2cFieldLabel}>
                  Name
                </label>
                <input
                  id="profile-name"
                  type="text"
                  value={user.name}
                  disabled
                  className={b2cSettingsFieldInputDisabled}
                />
              </div>

              <div>
                <label htmlFor="profile-email" className={b2cFieldLabel}>
                  Email
                </label>
                <input
                  id="profile-email"
                  type="email"
                  value={user.email}
                  disabled
                  className={b2cSettingsFieldInputDisabled}
                />
              </div>

              <WorkspaceList user={user} />
            </B2CPanelCardBody>
            <B2CPanelCardFooter>
              <ModalSecondaryButton
                type="button"
                onClick={() => setIsPasswordModalOpen(true)}
                className="gap-2"
              >
                <HiOutlineKey className="h-4 w-4" aria-hidden />
                Change Password
              </ModalSecondaryButton>
            </B2CPanelCardFooter>
          </B2CPanelCard>
        )}
      </AsyncBoundary>

      {isPasswordModalOpen ? (
        <Modal
          width="400px"
          title="Update password"
          onClose={() => setIsPasswordModalOpen(false)}
        >
          <ChangePassword />
        </Modal>
      ) : null}
    </SettingsTabShell>
  );
}

/**
 * The workspaces this account reaches.
 *
 * Replaces the old screen's disabled "Exam" box. An exam was the only thing a
 * consumer account belonged to; an account now belongs to its own practice and
 * to any organisations that have it, which is the thing worth showing on a
 * screen that renders on all five arms.
 */
function WorkspaceList({ user }: { user: Me }) {
  const memberships = user.memberships ?? [];
  if (memberships.length === 0) return null;

  return (
    <div>
      <p className={b2cFieldLabel}>Workspaces</p>
      <ul className="mt-1.5 divide-y divide-b2c-border rounded-xl border border-b2c-border">
        {memberships.map((membership) => (
          <li
            key={membership.org_slug}
            className="flex items-center justify-between gap-4 px-4 py-3"
          >
            <span className="flex min-w-0 items-center gap-2 text-osce-body text-osce-ink-900">
              <HiOutlineIdentification
                className="h-4 w-4 shrink-0 text-b2c-text-muted"
                aria-hidden
              />
              <span className="truncate">{membership.org_name ?? membership.org_slug}</span>
            </span>
            <span className="shrink-0 text-osce-meta capitalize text-b2c-text-muted">
              {membership.role.replace(/_/g, " ")}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
