"use client";

import type { ReactNode } from "react";
import { HiOutlineClock, HiOutlineEnvelope, HiOutlineUser } from "react-icons/hi2";
import { LuFilePen, LuUserCog } from "react-icons/lu";
import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader } from "@/foundation/ui/B2CPanelCard";
import type { DirectoryUser, PlatformUserDetail } from "@/domains/platform/api";
import { formatDay, formatMoment } from "@/domains/platform/support";
import { accessLabel, accessOf, accessTone, planLabel } from "@/domains/platform/users/vocabulary";
import { Badge } from "@/foundation/ui";
import { ProfileTab } from "@/domains/platform/user/ProfileTab";

type Detail = PlatformUserDetail & {
  consumer_role?: string | null;
  legacy_consumer_ids?: Record<string, string>;
};

function DetailRow({
  icon,
  label,
  value,
}: {
  icon?: ReactNode;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      {icon ? <span className="mt-0.5 shrink-0 text-b2c-text-muted">{icon}</span> : null}
      <div className="min-w-0 flex-1">
        <p className="text-osce-meta font-medium text-b2c-text-muted">{label}</p>
        <div className="text-osce-body text-ink">{value}</div>
      </div>
    </div>
  );
}

function StatusRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-osce-body text-b2c-text-secondary">{label}</span>
      {children}
    </div>
  );
}

/**
 * The retiring B2C admin's two top cards — basic information and account
 * status — with the platform's edit form underneath.
 */
export function B2cUserOverview({
  user,
  facts,
  onSaved,
}: {
  user: Detail;
  facts: DirectoryUser | null;
  onSaved: (user: PlatformUserDetail) => void;
}) {
  const exam = (user.exam_code ?? "sca").toLowerCase();
  const legacyId = user.legacy_consumer_ids?.[exam] ?? Object.values(user.legacy_consumer_ids ?? {})[0];
  const access = facts ? accessOf(facts) : null;
  const liveAccess =
    facts && (facts.live_exam_codes ?? []).length > 0
      ? `${(facts.live_exam_codes ?? []).map((code) => code.toUpperCase()).join(", ")}${
          facts.access_ends_at ? ` · until ${formatDay(facts.access_ends_at)}` : ""
        }`
      : "No live access";

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-osce-meta text-b2c-text-muted">User profile</p>
        {legacyId ? (
          <p className="mt-1 flex items-center gap-2 text-osce-body text-b2c-text-muted">
            <HiOutlineUser className="h-3.5 w-3.5 shrink-0" aria-hidden />
            <span className="truncate font-mono text-xs">{legacyId}</span>
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>Basic information</B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-4">
            <DetailRow icon={<HiOutlineEnvelope className="h-4 w-4" />} label="Email" value={user.email} />
            <DetailRow
              icon={<HiOutlineUser className="h-4 w-4" />}
              label="Username"
              value={<span className="capitalize">{user.name || "—"}</span>}
            />
            <DetailRow
              icon={<LuUserCog className="h-4 w-4" />}
              label="Role"
              value={user.consumer_role === "admin" ? "Admin" : "User"}
            />
            <DetailRow icon={<HiOutlineClock className="h-4 w-4" />} label="Member since" value={formatDay(user.created_at)} />
            <DetailRow icon={<LuFilePen className="h-4 w-4" />} label="Exam date" value={user.exam_date ? formatDay(user.exam_date) : "Unknown"} />
          </B2CPanelCardBody>
        </B2CPanelCard>

        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>Account status</B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-3">
            <StatusRow label="Payment status">
              {access ? (
                <Badge tone={accessTone(access)}>{accessLabel(access)}</Badge>
              ) : (
                <span className="text-osce-body text-b2c-text-secondary">—</span>
              )}
            </StatusRow>
            <StatusRow label="Login status">
              <span
                className={`rounded-md px-2.5 py-1 text-osce-caption font-medium ${
                  facts?.signed_in ? "bg-osce-success-bg text-osce-success-text" : "bg-b2c-secondary text-b2c-text-secondary"
                }`}
              >
                {facts?.signed_in ? "Online" : "Offline"}
              </span>
            </StatusRow>
            <StatusRow label="Last login">
              <span className="text-osce-body text-b2c-text-secondary">
                {user.last_login_at ? formatMoment(user.last_login_at) : "Never"}
              </span>
            </StatusRow>
            <StatusRow label="Exam type">
              <span className="text-osce-body text-b2c-text-secondary">{exam.toUpperCase()}</span>
            </StatusRow>
            <StatusRow label="Plan">
              <span className="text-osce-body font-medium text-ink">
                {facts?.has_paid ? planLabel(facts.plan_code) : "Unpaid"}
              </span>
            </StatusRow>
            <StatusRow label="Access">
              <span className="text-osce-body text-b2c-text-secondary">{liveAccess}</span>
            </StatusRow>
            <StatusRow label="Extra reading">
              <span className="text-osce-body text-b2c-text-secondary">
                {user.extra_reading_percent > 0 ? `${user.extra_reading_percent}%` : "None"}
              </span>
            </StatusRow>
          </B2CPanelCardBody>
        </B2CPanelCard>
      </div>

      <ProfileTab user={user} onSaved={onSaved} />
    </div>
  );
}
