"use client";

import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import Link from "next/link";
import {
  HiOutlineBuildingOffice2,
  HiOutlineCamera,
  HiOutlineCheck,
  HiOutlineKey,
} from "react-icons/hi2";
import { AsyncBoundary, Button, Input, Modal } from "@/foundation/ui";
import { getButtonClassName } from "@/foundation/ui/buttonStyles";
import Alert from "@/foundation/forms/Alert";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { isPlatformAdmin, useSession } from "@/foundation/session";
import { useCurrentExam } from "@/foundation/session/useCurrentExam";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readMe, updateMe, uploadAvatar, type Me } from "@/capabilities/account/api";
import { examLabel } from "@/capabilities/account/settings/examLabel";
import ChangePassword from "@/capabilities/account/settings/ChangePassword";
import CvPanel from "@/capabilities/account/settings/CvPanel";
import { CloseAccount } from "@/capabilities/account/settings/CloseAccount";
import { DownloadMyData } from "@/capabilities/account/settings/DownloadMyData";
import {
  SettingsCard,
  SettingsTile,
  settingsMeta,
  settingsSub,
} from "@/capabilities/account/settings/SettingsKit";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import { TwoFactorPanel } from "@/capabilities/account/settings/TwoFactorPanel";

/** The retiring client's `profileSchema`, kept as numbers so the copy is one string. */
const NAME_MIN = 3;
const NAME_MAX = 50;

/**
 * Who you are, and the two things about it you can change.
 *
 * The canvas's Profile tab (`train-settings`): Account, two-factor sign-in,
 * organisations, your data, and deleting the account. The name is editable
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
  const { codes, name: examName } = useCurrentExam();
  const holdsOrtho = codes.includes("ortho");

  return (
    <SettingsTabShell>
      <AsyncBoundary state={me}>
        {(user: Me) => (
          <>
            <AccountForm
              key={user.id}
              user={user}
              exam={examLabel(examName, user.exam_code ?? codes[0] ?? "sca")}
              onSaved={() => me.reload()}
              onDirtyChange={onDirtyChange}
            />
            <TwoFactorPanel />
            <Organisations user={user} />
          </>
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
      <SettingsCard title="Account" description="Your sign-in details and account actions.">
        <div className="space-y-4">
          {successMessage ? <Alert message={successMessage} type="success" /> : null}
          {error ? <Alert message={error} type="error" /> : null}
          {avatarError ? <Alert message={avatarError} type="error" /> : null}

          <div className="flex items-center gap-4">
            {avatarUrl ? (
              // A private, per-account S3 URL, not a build-time asset.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={avatarUrl} alt="" className="h-16 w-16 rounded-full object-cover" />
            ) : (
              <div
                className="flex h-16 w-16 items-center justify-center rounded-full bg-canvas text-[21px] font-semibold text-ink"
                aria-hidden
              >
                {initials(user.name || user.email)}
              </div>
            )}
            <label
              htmlFor="avatar-upload"
              className={getButtonClassName({ variant: "secondary", className: "cursor-pointer gap-2" })}
            >
              <HiOutlineCamera className="h-4 w-4" aria-hidden />
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

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              id="username"
              label="Username"
              value={name}
              onChange={(event) => setName(event.target.value)}
              error={fieldError ?? undefined}
            />
            <Input id="email" type="email" label="Email" value={user.email} disabled />
          </div>

          <Input id="exam" label="Exam" value={exam} disabled />

          <div className="flex flex-wrap justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsPasswordModalOpen(true)}
              className="gap-2"
            >
              <HiOutlineKey className="h-4 w-4" aria-hidden />
              Change password
            </Button>
            <Button type="submit" isLoading={saving} className="gap-2">
              <HiOutlineCheck className="h-4 w-4" aria-hidden />
              Update profile
            </Button>
          </div>
        </div>
      </SettingsCard>

      {isPasswordModalOpen ? (
        <Modal width="400px" title="Update password" onClose={() => setIsPasswordModalOpen(false)}>
          <ChangePassword />
        </Modal>
      ) : null}
    </form>
  );
}

/** "Amina Khan" reads AK; a single word, or an address, gives its first letter. */
function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const first = words[0]?.[0] ?? "";
  const last = words.length > 1 ? (words[words.length - 1]?.[0] ?? "") : "";
  return (first + last).toUpperCase();
}

/**
 * The organisations this account belongs to, and what they can see.
 *
 * There is no route for leaving one from here: an organisation's admin removes
 * a member, so the card says who has you and does not offer a button that
 * would do nothing.
 */
function Organisations({ user }: { user: Me }) {
  const { hrefFor } = useSurface();
  const memberships = user.memberships ?? [];
  if (memberships.length === 0) return null;

  return (
    <SettingsCard title="Organisations">
      <div className="space-y-3">
        {memberships.map((membership) => (
          <div key={membership.org_slug} className="flex items-center gap-3">
            <SettingsTile icon={HiOutlineBuildingOffice2} size="md" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-osce-body font-medium text-ink">
                {membership.org_name ?? membership.org_slug}
              </p>
              <p className={`${settingsMeta} capitalize`}>{membership.role.replace(/_/g, " ")}</p>
            </div>
          </div>
        ))}
        <p className={settingsSub}>
          They see your sittings, marks, released results and practice on their stations. They never
          see your personal practice, debriefs, plan or Athena&apos;s notes unless you share a station
          for review.
        </p>
        <Link
          href={`${hrefFor("/settings")}?tab=payments`}
          className="inline-block text-osce-data font-medium text-accent hover:text-accent-hover"
        >
          How this affects your plan
        </Link>
      </div>
    </SettingsCard>
  );
}
