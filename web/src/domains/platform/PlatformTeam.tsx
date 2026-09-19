"use client";

import { LuShieldCheck } from "react-icons/lu";
import { AsyncBoundary, Badge } from "@/foundation/ui";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { useAsync } from "@/foundation/hooks";
import { listPlatformAdmins } from "@/domains/platform/api";
import { Row, RowList, Section } from "@/domains/platform/chrome";
import { formatDay } from "@/domains/platform/support";

export function PlatformTeam() {
  const state = useAsync((signal) => listPlatformAdmins(signal), []);

  return (
    <div className="flex flex-col gap-8">
      <PlatformPageHeader
        title="Platform team"
        description="Everyone who may open this staff console."
        icon={LuShieldCheck}
      />

      <Section title="Administrators">
        <AsyncBoundary
          state={state}
          isEmpty={(rows) => rows.length === 0}
          empty={{
            title: "No platform administrators",
            description: "Grant console access from a user's profile.",
          }}
        >
          {(admins) => (
            <RowList>
              {admins.map((user) => (
                <Row key={user.id}>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{user.email}</p>
                    <p className="truncate text-xs text-ink-subtle">
                      {user.name || "No name"} · joined {formatDay(user.created_at)}
                    </p>
                  </div>
                  <Badge tone="success">
                    <LuShieldCheck className="mr-1 h-3 w-3" aria-hidden />
                    Console
                  </Badge>
                </Row>
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Section>
    </div>
  );
}
