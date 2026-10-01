"use client";

import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import {
  HiOutlineArrowPath,
  HiOutlineCheckCircle,
  HiOutlineIdentification,
  HiOutlineKey,
} from "react-icons/hi2";
import {
  AsyncBoundary,
  Modal,
  ModalHelper,
  ModalPrimaryButton,
  ModalSecondaryButton,
  Panel,
  productTokens,
} from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { isPlatformAdmin, useSession } from "@/foundation/session";
import { useCurrentExam } from "@/foundation/session/useCurrentExam";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readMe, updateMe, uploadAvatar, type Me } from "@/capabilities/account/api";
import ChangePassword from "@/capabilities/account/settings/ChangePassword";
import CvPanel from "@/capabilities/account/settings/CvPanel";
import { CloseAccount } from "@/capabilities/account/settings/CloseAccount";
import { DownloadMyData } from "@/capabilities/account/settings/DownloadMyData";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cSettingsFieldInput, b2cSettingsFieldInputDisabled } = productTokens;

/** The retiring client's `profileSchema`, kept as numbers so the copy is one string. */
const NAME_MIN = 3;
const NAME_MAX = 50;

/**
 * Who you are, and the two things about it you can change.
 *
 * The retiring client's Profile tab, card for card: the "Account" card with
 * Username, Email and Exam, then the "Danger zone". The name is editable
 * because `PATCH /me` accepts it. The address stays read back: changing the
 * thing you sign in with is a different flow with its own verification, and no
 * `platform-api` route does it.
 *
 * `onDirtyChange` tells the tab strip an edited username is unsaved, so the
 * old screen's leave guard can stop a tab switch.
 */
export default function ProfilePanel({
  onDirtyChange,
}: {
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const me = useAsync((signal) => readMe(signal), []);
  const { session } = useSession();
  const { codes } = useCurrentExam();
  const holdsOrtho = codes.includes("ortho");

  return (
    <SettingsTabShell>
      <AsyncBoundary state={me}>
        {(user: Me) => (
          <AccountForm
            key={user.id}
            user={user}
            // The old screen printed the raw app type ("sca"), not a label.
            exam={user.exam_code ?? codes[0] ?? "sca"}
            onSaved={() => me.reload()}
            onDirtyChange={onDirtyChange}
          />
        )}
      </AsyncBoundary>

      {/*
        The CV, for the one arm that is scored off a portfolio. The orthopaedic
        interview reads a portfolio rather than a consultation, so this is the
        material the practice questions are generated from — and `POST /cv` had
        been served for weeks with no screen calling it. Gated on holding the
        exam rather than shown to everybody, which is how the old profile had it.
      */}
      {holdsOrtho ? <CvPanel /> : null}
      <DownloadMyData />
      <CloseAccount isAdmin={isPlatformAdmin(session)} />
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
function AccountForm({
  user,
  exam,
  onSaved,
  onDirtyChange,
}: {
  user: Me;
  exam: string;
  onSaved: () => void;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const { refresh } = useSession();
  const [name, setName] = useState(user.name);
  const [savedName, setSavedName] = useState(user.name);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState(user.avatar_url ?? null);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);

  const onAvatarPicked = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setAvatarBusy(true);
    setAvatarError(null);
    try {
      const updated = await uploadAvatar(file);
      setAvatarUrl(updated.avatar_url ?? null);
      await refresh();
      onSaved();
    } catch (cause) {
      setAvatarError(errorMessage(cause));
    } finally {
      setAvatarBusy(false);
    }
  };

  useEffect(() => {
    onDirtyChange?.(name !== savedName);
    return () => onDirtyChange?.(false);
  }, [name, savedName, onDirtyChange]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    setError("");
    setSuccessMessage("");
    if (trimmed.length < NAME_MIN) {
      setFieldError(`Username must be at least ${NAME_MIN} characters`);
      return;
    }
    if (trimmed.length > NAME_MAX) {
      setFieldError(`Username must be less than ${NAME_MAX} characters`);
      return;
    }
    setFieldError(null);
    setSaving(true);
    try {
      await updateMe({ name: trimmed });
      setSavedName(trimmed);
      await refresh();
      setSuccessMessage("Profile updated");
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={(event) => void submit(event)}>
      <Panel title="Account">
        <div className="space-y-4">
          <ModalHelper className="mt-0">Your sign-in details and account actions.</ModalHelper>

          {successMessage ? <Alert message={successMessage} type="success" /> : null}
          {error ? <Alert message={error} type="error" /> : null}
          {avatarError ? <Alert message={avatarError} type="error" /> : null}

          <div className="flex items-center gap-4">
            {avatarUrl ? (
              // A private, per-account S3 URL, not a build-time asset.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={avatarUrl}
                alt=""
                className="h-14 w-14 rounded-full border border-border object-cover"
              />
            ) : (
              <div
                className="flex h-14 w-14 items-center justify-center rounded-full border border-border bg-canvas text-osce-body text-ink-subtle"
                aria-hidden
              >
                {(user.name || user.email).slice(0, 1).toUpperCase()}
              </div>
            )}
            <div>
              <label
                htmlFor="avatar-upload"
                className="inline-block cursor-pointer text-osce-meta font-medium text-accent"
              >
                {avatarBusy ? "Uploading…" : "Change photo"}
              </label>
              <input
                id="avatar-upload"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                disabled={avatarBusy}
                onChange={(event) => void onAvatarPicked(event)}
              />
            </div>
          </div>

          <div>
            <label htmlFor="username" className={b2cFieldLabel}>
              Username
            </label>
            <input
              type="text"
              id="username"
              value={name}
              onChange={(event) => setName(event.target.value)}
              aria-invalid={fieldError ? true : undefined}
              className={`mt-1.5 ${b2cSettingsFieldInput} ${fieldError ? "border-osce-danger" : ""}`}
            />
            {fieldError ? (
              <p className="mt-1 text-osce-meta text-osce-danger">{fieldError}</p>
            ) : null}
          </div>

          <div>
            <label htmlFor="email" className={b2cFieldLabel}>
              Email
            </label>
            <input
              type="email"
              id="email"
              value={user.email}
              disabled
              className={b2cSettingsFieldInputDisabled}
            />
          </div>

          <div>
            <label htmlFor="exam" className={b2cFieldLabel}>
              Exam
            </label>
            <input
              type="text"
              id="exam"
              value={exam}
              disabled
              className={b2cSettingsFieldInputDisabled}
            />
          </div>

          <WorkspaceList user={user} />
        </div>
        <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
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
        </div>
      </Panel>

      {isPasswordModalOpen ? (
        <Modal width="400px" title="Update password" onClose={() => setIsPasswordModalOpen(false)}>
          <ChangePassword />
        </Modal>
      ) : null}
    </form>
  );
}

/**
 * The workspaces this account reaches — on the institution arms only.
 *
 * An exam was the only thing a consumer account belonged to, and the consumer
 * screen shows exactly what the old one did. An account on an institution arm
 * also belongs to the organisations that have it, which is worth a list there.
 */
function WorkspaceList({ user }: { user: Me }) {
  const { surface } = useSurface();
  const memberships = user.memberships ?? [];
  if (surface === "train" || memberships.length === 0) return null;

  return (
    <div>
      <p className={b2cFieldLabel}>Workspaces</p>
      <ul className="mt-1.5 divide-y divide-border rounded-xl border border-border">
        {memberships.map((membership) => (
          <li
            key={membership.org_slug}
            className="flex items-center justify-between gap-4 px-4 py-3"
          >
            <span className="flex min-w-0 items-center gap-2 text-osce-body text-ink">
              <HiOutlineIdentification
                className="h-4 w-4 shrink-0 text-ink-subtle"
                aria-hidden
              />
              <span className="truncate">{membership.org_name ?? membership.org_slug}</span>
            </span>
            <span className="shrink-0 text-osce-meta capitalize text-ink-subtle">
              {membership.role.replace(/_/g, " ")}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
