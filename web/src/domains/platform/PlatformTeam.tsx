"use client";

import { useCallback, useState } from "react";
import { LuShieldCheck } from "react-icons/lu";
import {
  AsyncBoundary,
  Badge,
  Button,
  ConfirmModal,
  Panel,
  PlatformPageHeader,
  Row,
  RowList,
} from "@/foundation/ui";
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
      <PlatformPageHeader
        title="Platform team"
        description="Everyone who may open this staff console."
        icon={LuShieldCheck}
        actions={
          <Button variant="primary" onClick={() => setInviteOpen(true)}>
            Add team member
          </Button>
        }
      />

      <InvitePlatformAdminModal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onInvited={() => state.reload()}
      />

      <Panel title="Administrators" padding="none">
        <AsyncBoundary
          state={state}
          isEmpty={(rows) => rows.length === 0}
          empty={{
            title: "No platform administrators",
            description:
              "Add someone by email. They will be invited to set a password if they are new.",
            action: (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setInviteOpen(true)}
              >
                Add team member
              </Button>
            ),
            bare: true,
          }}
        >
          {(admins) => (
            <RowList flush>
              {admins.map((user) => {
                const isSelf = selfId !== null && user.id === selfId;
                return (
                  <Row key={user.id}>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-osce-data font-medium text-ink">
                        {user.email}
                      </p>
                      <p className="truncate text-osce-meta text-ink-subtle">
                        {user.name || "No name"} · joined{" "}
                        {formatDay(user.created_at)}
                        {isSelf ? " · you" : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge tone="success">
                        <LuShieldCheck className="mr-1 h-3 w-3" aria-hidden />
                        Console
                      </Badge>
                      {isSelf ? null : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setRevokeTarget(user)}
                        >
                          Revoke
                        </Button>
                      )}
                    </div>
                  </Row>
                );
              })}
            </RowList>
          )}
        </AsyncBoundary>
      </Panel>

      <ConfirmModal
        isOpen={revokeTarget !== null}
        onCancel={() => {
          setRevokeTarget(null);
          setRevokeError(null);
        }}
        onConfirm={() => void confirmRevoke()}
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
