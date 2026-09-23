"use client";

import { useState, type FormEvent } from "react";
import { LuUserCog } from "react-icons/lu";
import {
  HiOutlineArrowPath,
  HiOutlineCheckCircle,
  HiOutlineIdentification,
  HiOutlineKey,
} from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  Modal,
  ModalHelper,
  ModalPrimaryButton,
  ModalSecondaryButton,
  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useCurrentExam } from "@/foundation/session/useCurrentExam";
import { readMe, updateMe, type Me } from "@/capabilities/account/api";
import ChangePassword from "@/capabilities/account/settings/ChangePassword";
import CvPanel from "@/capabilities/account/settings/CvPanel";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const {
  b2cFieldLabel,
  b2cSettingsCardHeaderIcon,
  b2cSettingsFieldInput,
  b2cSettingsFieldInputDisabled,
} = productTokens;

/** The retiring client's `profileSchema`, kept as numbers so the copy is one string. */
const NAME_MIN = 3;
const NAME_MAX = 50;

/**
 * Who you are, and the two things about it you can change.
 *
 * The name is editable because `PATCH /me` accepts it. The address stays read
 * back: changing the thing you sign in with is a different flow with its own
 * verification, and no `platform-api` route does it. The retiring screen's
 * "Danger zone" is still absent — soft-deleting an account has no endpoint
 * here either, and a button that cannot save is worse than no button.
 */
export default function ProfilePanel() {
  const me = useAsync((signal) => readMe(signal), []);
  const { codes } = useCurrentExam();
  const holdsOrtho = codes.includes("ortho");

  return (
    <SettingsTabShell>
      <AsyncBoundary state={me}>
        {(user: Me) => <AccountForm key={user.id} user={user} onSaved={() => me.reload()} />}
      </AsyncBoundary>

      {/*
        The CV, for the one arm that is scored off a portfolio. The orthopaedic
        interview reads a portfolio rather than a consultation, so this is the
        material the practice questions are generated from — and `POST /cv` had
        been served for weeks with no screen calling it. Gated on holding the
        exam rather than shown to everybody, which is how the old profile had it.
      */}
      {holdsOrtho ? <CvPanel /> : null}
    </SettingsTabShell>
  );
}

/**
 * The account card, with the name write and the password modal inside it.
 *
 * Saving refreshes the *session* as well as re-reading `/me`. The nav footer on
 * two arms prints `session.user.name`, so a patch that only re-reads the panel
 * leaves the rail calling you by the name you just retired.
 */
function AccountForm({ user, onSaved }: { user: Me; onSaved: () => void }) {
  const { refresh } = useSession();
  const [name, setName] = useState(user.name);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    setError(null);
    setSaved(false);
    if (trimmed.length < NAME_MIN) {
      setFieldError(`Name must be at least ${NAME_MIN} characters`);
      return;
    }
    if (trimmed.length > NAME_MAX) {
      setFieldError(`Name must be less than ${NAME_MAX} characters`);
      return;
    }
    setFieldError(null);
    setSaving(true);
    try {
      await updateMe({ name: trimmed });
      await refresh();
      setSaved(true);
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={(event) => void submit(event)}>
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          <LuUserCog className={b2cSettingsCardHeaderIcon} aria-hidden />
          Account
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-4">
          <ModalHelper className="mt-0">
            Your sign-in details and account actions.
          </ModalHelper>

          {error ? <Alert tone="danger">{error}</Alert> : null}
          {saved ? <Alert tone="success">Profile updated.</Alert> : null}

          <div>
            <label htmlFor="profile-name" className={b2cFieldLabel}>
              Name
            </label>
            <input
              id="profile-name"
              type="text"
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                setSaved(false);
              }}
              aria-invalid={fieldError ? true : undefined}
              className={`${b2cSettingsFieldInput} mt-1.5${
                fieldError ? " border-osce-danger" : ""
              }`}
            />
            {fieldError ? (
              <p className="mt-1 text-osce-meta text-osce-danger">{fieldError}</p>
            ) : null}
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
          <ModalPrimaryButton type="submit" disabled={saving} className="gap-2">
            {saving ? (
              <>
                <HiOutlineArrowPath className="h-4 w-4 animate-spin" aria-hidden />
                Updating...
              </>
            ) : (
              <>
                <HiOutlineCheckCircle className="h-4 w-4" aria-hidden />
                Update Profile
              </>
            )}
          </ModalPrimaryButton>
        </B2CPanelCardFooter>
      </B2CPanelCard>

      {isPasswordModalOpen ? (
        <Modal
          width="400px"
          title="Update password"
          onClose={() => setIsPasswordModalOpen(false)}
        >
          <ChangePassword />
        </Modal>
      ) : null}
    </form>
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
