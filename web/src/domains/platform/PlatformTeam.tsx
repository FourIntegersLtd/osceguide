"use client";

import { useCallback, useState } from "react";
import {
  AsyncBoundary,
  Badge,
  Button,
  ConfirmModal,
  B2CPageHeader,
} from "@/foundation/ui";
import Table from "@/foundation/table/Table";
import { InvitePlatformAdminModal } from "@/domains/platform/InvitePlatformAdminModal";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  listPlatformAdmins,
  setPlatformAdmin,
  type User,
} from "@/domains/platform/api";
import { formatDay } from "@/domains/platform/support";
import { useSession } from "@/foundation/session";

export function PlatformTeam() {
  const { session } = useSession();
  const toast = useToast();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<User | null>(null);
  const [revokeBusy, setRevokeBusy] = useState(false);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  const state = useAsync((signal) => listPlatformAdmins(signal), []);

  const selfId = session?.user.id ?? null;

  const confirmRevoke = useCallback(async () => {
    if (!revokeTarget) return;
    setRevokeBusy(true);
    setRevokeError(null);
    try {
      await setPlatformAdmin(revokeTarget.id, false);
      toast.success(`Revoked console access for ${revokeTarget.email}`);
      setRevokeTarget(null);
      state.reload();
    } catch (cause) {
      setRevokeError(errorMessage(cause));
    } finally {
      setRevokeBusy(false);
    }
  }, [revokeTarget, state, toast]);

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Platform team"
        action={
          <Button themeType="b2b" variant="commit" onClick={() => setInviteOpen(true)}>
            Add team member
          </Button>
        }
      />

      <InvitePlatformAdminModal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onInvited={() => state.reload()}
      />

      <AsyncBoundary
        state={state}
        isEmpty={(rows) => rows.length === 0}
        empty={{
          title: "No platform administrators",
          description:
            "Add someone by email. They will be invited to set a password if they are new.",
          action: (
            <Button
              themeType="b2b"
              variant="secondary"
              size="sm"
              onClick={() => setInviteOpen(true)}
            >
              Add team member
            </Button>
          ),
        }}
      >
        {(admins) => (
          <Table<User>
            rows={admins}
            themeType="b2b"
            idField="id"
            title="Administrators"
            columns={[
              {
                header: "Member",
                key: "email",
                priority: "primary",
                render: (user) => (
                  <div className="min-w-0">
                    <p className="truncate font-medium text-ink">{user.email}</p>
                    <p className="truncate text-osce-meta text-ink-subtle">
                      {user.name || "No name"} · joined {formatDay(user.created_at)}
                      {selfId !== null && user.id === selfId ? " · you" : ""}
                    </p>
                  </div>
                ),
              },
              {
                header: "Access",
                key: "is_platform_admin" as keyof User,
                render: () => (
                  <Badge tone="success" dot>
                    Console
                  </Badge>
                ),
              },
              {
                header: "",
                key: "id",
                render: (user) =>
                  selfId !== null && user.id === selfId ? null : (
                    <Button
                      themeType="b2b"
                      variant="ghost"
                      size="sm"
                      onClick={() => setRevokeTarget(user)}
                    >
                      Revoke
                    </Button>
                  ),
              },
            ]}
          />
        )}
      </AsyncBoundary>

      <ConfirmModal
        isOpen={revokeTarget !== null}
        onCancel={() => {
          setRevokeTarget(null);
          setRevokeError(null);
        }}
        onConfirm={() => confirmRevoke()}
        isLoading={revokeBusy}
        error={revokeError}
        tone="danger"
        title="Revoke staff console access?"
        confirmText="Revoke"
        message={
          revokeTarget
            ? `${revokeTarget.email} will lose this console. Their organisation memberships are untouched.`
            : ""
        }
      />
    </div>
  );
}
