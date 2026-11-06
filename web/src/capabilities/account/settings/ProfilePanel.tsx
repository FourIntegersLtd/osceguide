"use client";

import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import Link from "next/link";
import {
  HiOutlineAcademicCap,
  HiOutlineBuildingOffice2,
  HiOutlineCamera,
  HiOutlineCheck,
  HiOutlineKey,
} from "react-icons/hi2";
import { AsyncBoundary, Input, Modal, Panel } from "@/foundation/ui";
import { boardAvatar, boardInput, boardLabel, boardButtonSmall } from "@/foundation/ui/boardKit";
import { cn } from "@/foundation/ui/cn";
import { getButtonClassName } from "@/foundation/ui/buttonStyles";
import Alert from "@/foundation/forms/Alert";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { isPlatformAdmin, useSession } from "@/foundation/session";
import { useCurrentExam } from "@/foundation/session/useCurrentExam";
import { isOrgSurface } from "@/capabilities/surface";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readMe, updateMe, uploadAvatar, type Me } from "@/capabilities/account/api";
import type { ProfilePart } from "@/capabilities/account/settings/settingsTabs";
import {
  AVATAR_CAPTION,
  AVATAR_MAX_BYTES,
  AVATAR_TOO_BIG,
} from "@/capabilities/account/settings/avatarRule";
import { examLabel, NO_EXAM_LABEL } from "@/capabilities/account/settings/examLabel";
import ChangeEmail from "@/capabilities/account/settings/ChangeEmail";
import ChangePassword from "@/capabilities/account/settings/ChangePassword";
import CvPanel from "@/capabilities/account/settings/CvPanel";
import { CloseAccount } from "@/capabilities/account/settings/CloseAccount";
import { DownloadMyData } from "@/capabilities/account/settings/DownloadMyData";
import { AccountButton, AccountCard, useBoardSkin } from "@/capabilities/account/settings/AccountKit";
import { SettingsRow, SettingsRows, SettingsTile, settingsMeta, settingsSub } from "@/capabilities/account/settings/SettingsKit";
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
 *
 * `part` shows one third of it. Staff settings split the tab in three
 * (Account, Security, Data) because staff have no exam, plan or tutor, so
 * Profile was the only tab with anything of theirs on it.
 */

export default function ProfilePanel({
  onDirtyChange,
  part,
}: {
  onDirtyChange?: (dirty: boolean) => void;
  part?: ProfilePart;
}) {
  const me = useAsync((signal) => readMe(signal), []);
  const { session } = useSession();
  const { code, codes, name: examName } = useCurrentExam();
  const shows = (wanted: ProfilePart) => part === undefined || part === wanted;
  // An organisation's cards run the width of the page, as the Settings board draws them.
  const board = useBoardSkin();

  return (
    <SettingsTabShell fullWidth={board}>
      {shows("account") ? (
        <AsyncBoundary state={me}>
          {(user: Me) => (
            <>
              <AccountForm
                key={user.id}
                user={user}
                // The split (staff) screen has its own Security tab, and staff hold no exam.
                exam={part ? null : examLabel(examName, user.exam_code ?? codes[0]) ?? NO_EXAM_LABEL}
                passwordHere={part === undefined}
                onSaved={() => me.reload()}
                onDirtyChange={onDirtyChange}
              />
              {part === undefined ? <TwoFactorPanel /> : null}
              <Organisations user={user} />
            </>
          )}
        </AsyncBoundary>
      ) : null}
      {part === "security" ? (
        <>
          <Panel title="Password" description="Change the password you sign in with">
            <ChangePassword />
          </Panel>
          <Panel title="Email" description="Change the address you sign in with">
            <ChangeEmail />
          </Panel>
          <TwoFactorPanel />
        </>
      ) : null}

      {/*
        The CV, for the one arm that is scored off a portfolio. The orthopaedic
        interview reads a portfolio rather than a consultation, so this is the
        material the practice questions are generated from — and `POST /cv` had
        been served for weeks with no screen calling it. Shown only while Ortho is
        the current exam, not whenever it is one of the exams held.
      */}
      {code === "ortho" && part === undefined ? <CvPanel /> : null}
      {shows("data") ? (
        <>
          <DownloadMyData />
          <CloseAccount isAdmin={isPlatformAdmin(session)} />
        </>
      ) : null}
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
  passwordHere,
  onSaved,
  onDirtyChange,
}: {
  user: Me;
  exam: string | null;
  passwordHere: boolean;
  onSaved: () => void;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const { refresh } = useSession();
  const board = useBoardSkin();
  const [name, setName] = useState(user.name);
  const [savedName, setSavedName] = useState(user.name);
  const [saving, setSaving] = useState(false);
  const toast = useToast();
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
    if (file.size > AVATAR_MAX_BYTES) {
      toast.error(AVATAR_TOO_BIG);
      return;
    }
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
      toast.success("Profile updated");
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={(event) => void submit(event)}>
      <AccountCard title="Account" description="Your sign-in details and account actions">
        <div className={board ? "flex flex-col gap-3" : "space-y-4"}>
          {error ? <Alert message={error} type="error" /> : null}
          {avatarError ? <Alert message={avatarError} type="error" /> : null}

          <div className={board ? "flex items-center gap-3" : "flex items-center gap-4"}>
            {avatarUrl ? (
              // A private, per-account S3 URL, not a build-time asset.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={avatarUrl} alt="" className={board ? "h-14 w-14 rounded-full object-cover" : "h-16 w-16 rounded-full object-cover"} />
            ) : (
              <div
                className={
                  board
                    ? `${boardAvatar} !h-14 !w-14`
                    : "flex h-16 w-16 items-center justify-center rounded-full bg-canvas text-[21px] font-semibold text-ink"
                }
                aria-hidden
              >
                {initials(user.name || user.email)}
              </div>
            )}
            <div className="space-y-1">
              <label
                htmlFor="avatar-upload"
                className={
                  board
                    ? boardButtonSmall + " cursor-pointer"
                    : getButtonClassName({ variant: "secondary", className: "cursor-pointer gap-2" })
                }
              >
                {board ? null : <HiOutlineCamera className="h-4 w-4" aria-hidden />}
                {avatarBusy ? "Uploading…" : avatarUrl ? "Change photo" : "Add photo"}
              </label>
              <p className={settingsMeta}>{AVATAR_CAPTION}</p>
            </div>
            <input
              id="avatar-upload"
              type="file"
              accept="image/jpeg,image/png"
              className="hidden"
              disabled={avatarBusy}
              onChange={(event) => void onAvatarPicked(event)}
            />
          </div>

          {board ? (
            <>
              <div>
                <label htmlFor="username" className={`${boardLabel} !mb-2`}>Username</label>
                <input
                  id="username"
                  className={cn(boardInput, fieldError ? "border-osce-danger-text" : undefined)}
                  value={name}
                  aria-invalid={fieldError ? true : undefined}
                  aria-describedby={fieldError ? "username-error" : undefined}
                  onChange={(event) => setName(event.target.value)}
                />
                {fieldError ? <p id="username-error" role="alert" className="mt-1.5 text-assess-meta leading-normal text-osce-danger-text">{fieldError}</p> : null}
              </div>
              <div>
                <label htmlFor="email" className={`${boardLabel} !mb-2`}>Email</label>
                <input id="email" type="email" className={`${boardInput} disabled:bg-osce-canvas`} value={user.email} disabled />
              </div>
            </>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input
                id="username"
                label="Username"
                value={name}
                onChange={(event) => setName(event.target.value)}
                error={fieldError ?? undefined}
              />
              <Input id="email" type="email" label="Email" value={user.email} disabled />
            </div>
          )}

          {/* The board has no exam row: an organisation member holds no practice exam until they choose one. */}
          {exam !== null && !(board && exam === NO_EXAM_LABEL) ? (
            <SettingsRows>
              <SettingsRow
                icon={HiOutlineAcademicCap}
                title="Exam type"
                meta="Chosen at sign-up. Contact us to change it"
                trailing={<span className="text-osce-body text-ink">{exam}</span>}
              />
            </SettingsRows>
          ) : null}

          <div className={board ? "flex flex-wrap gap-2" : "flex flex-wrap justify-end gap-2"}>
            {passwordHere ? (
              <AccountButton variant="secondary" icon={HiOutlineKey} onClick={() => setIsPasswordModalOpen(true)}>
                Change password
              </AccountButton>
            ) : null}
            <AccountButton type="submit" icon={HiOutlineCheck} isLoading={saving}>
              Update profile
            </AccountButton>
          </div>
        </div>
      </AccountCard>

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
  const { hrefFor, surface } = useSurface();
  const consumer = !isOrgSurface(surface);
  const memberships = user.memberships ?? [];
  if (memberships.length === 0) return null;

  const sees = consumer
    ? "They see your sittings, marks, released results and practice on their stations. They never see your personal practice, debriefs, plan or Athena\u2019s notes unless you share a station for review."
    : "They see your sittings, marks, released results and practice on their stations.";

  if (!consumer) {
    // The Settings board: the sentence under the title, then one row per organisation with the role at the right.
    return (
      <AccountCard title="Organisations" description={sees}>
        <div className="flex flex-col">
          {memberships.map((membership) => (
            <div key={membership.org_slug} className="flex items-center gap-2 py-4 text-assess-label text-ink">
              <HiOutlineBuildingOffice2 className="h-4 w-4 flex-none text-ink-muted" aria-hidden />
              <span className="min-w-0 flex-1 truncate">{membership.org_name ?? membership.org_slug}</span>
              <span className="text-assess-meta capitalize text-ink-muted">{membership.role.replace(/_/g, " ")}</span>
            </div>
          ))}
        </div>
      </AccountCard>
    );
  }

  return (
    <Panel title="Organisations">
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
        <p className={settingsSub}>{sees}</p>
        <Link
          href={`${hrefFor("/settings")}?tab=payments`}
          className="inline-block text-osce-data font-medium text-accent hover:text-accent-hover"
        >
          How this affects your plan
        </Link>
      </div>
    </Panel>
  );
}
