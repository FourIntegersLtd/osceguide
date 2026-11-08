"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import type { Workspace } from "@/foundation/routing";
import { workspaceBasePath } from "@/foundation/routing";
import { can, useSession } from "@/foundation/session";
import { ButtonLink } from "@/foundation/ui";
import { EmptyState } from "@/foundation/ui/EmptyState";
import type { SurfaceManifest } from "@/surfaces/contract";

/**
 * What a screen this arm leaves out on purpose says, with no api call: a way back to the
 * person's own home (the Overview for staff, My assessments for a candidate).
 */
export function RefusedScreen({
  refusal,
  workspace,
}: {
  refusal: NonNullable<SurfaceManifest["refusal"]>;
  workspace: Workspace;
}) {
  const { session } = useSession();
  const words = useAssessWords();
  const staff = can(session, "run_circuits");
  const base = workspaceBasePath(workspace);
  return (
    <EmptyState
      title={refusal.title}
      titleAs="h1"
      description={refusal.body(workspace.name, staff)}
      action={
        <ButtonLink href={staff ? `${base}/dashboard` : `${base}/trainee`}>
          {staff ? `Go to ${words.Home}` : `Go to ${words.MyTraining.toLowerCase()}`}
        </ButtonLink>
      }
    />
  );
}
