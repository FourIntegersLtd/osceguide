"use client";

import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { useRouter } from "next/navigation";
import {
  HiOutlineArchiveBox,
  HiOutlineArrowLeft,
  HiOutlineArrowUpTray,
  HiOutlinePencilSquare,
} from "react-icons/hi2";
import { Alert, AsyncBoundary, Panel } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { useAsync } from "@/foundation/hooks";
import {
  addRubricVersion,
  archiveRubricVersion,
  publishRubricVersion,
  readRubric,
  type Rubric,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { useSurface } from "@/capabilities";
import { rubricEditPath } from "@/capabilities/authoring/templates/paths";

/** A rubric's versions, and the writes against each one. */
export function RubricDetail({ rubricId, onBack }: { rubricId: string; onBack: () => void }) {
  const scope = useAuthoringScope();
  const rubric = useAsync((signal) => readRubric(scope, rubricId, signal), [scope.base, rubricId]);
  const action = useAction(rubric.reload);
  const { hrefFor } = useSurface();
  const router = useRouter();
  const canAuthor = useCanAuthor();

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-osce-body font-medium text-accent hover:underline"
      >
        <HiOutlineArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
        Marking schemes
      </button>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <AsyncBoundary state={rubric}>
        {(data: Rubric) => (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-osce-body font-semibold text-ink">{data.title}</h2>
              {canAuthor ? (
              <AuthoringButton
                variant="secondary"
                size="sm"
                disabled={action.busy !== null}
                onClick={() => action.run("add", () => addRubricVersion(scope, data.id))}
              >
                {action.busy === "add" ? "Creating…" : "New draft version"}
              </AuthoringButton>
              ) : null}
            </div>

            {(data.versions ?? []).length === 0 ? (
              <Panel padding="md">
                <p className="text-osce-body text-ink-muted">
                  {canAuthor
                    ? "This marking scheme has no versions yet. Cut a draft to start writing it."
                    : "Nothing here yet."}
                </p>
              </Panel>
            ) : null}

            {[...(data.versions ?? [])]
              .sort((a, b) => b.version - a.version)
              .map((version) => (
                <Panel key={version.id} padding="md">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-osce-body font-medium text-ink">
                        Version {version.version}
                      </p>
                      <p className="mt-0.5 line-clamp-2 text-osce-caption text-ink-muted">
                        {version.system_prompt || "No system prompt."}
                      </p>
                    </div>
                    <StatusBadge status={version.status} />
                  </div>
                  <div className="mt-3">
                    <AuthoringRowActions>
                      <AuthoringIconAction
                        label={version.status === "draft" && canAuthor ? "Edit in the builder" : "Open in the builder"}
                        onClick={() => router.push(rubricEditPath(hrefFor, data.id, version.version))}
                      >
                        <HiOutlinePencilSquare className="h-4 w-4" aria-hidden />
                      </AuthoringIconAction>
                      {canAuthor && version.status !== "published" ? (
                        <AuthoringIconAction
                          variant="primary"
                          label="Publish"
                          busy={action.busy === `publish:${version.id}`}
                          busyLabel="Publishing…"
                          disabled={action.busy !== null}
                          onClick={() =>
                            void action.run(`publish:${version.id}`, () =>
                              publishRubricVersion(scope, data.id, version.version),
                            )
                          }
                        >
                          <HiOutlineArrowUpTray className="h-4 w-4" aria-hidden />
                        </AuthoringIconAction>
                      ) : null}
                      {canAuthor && version.status !== "archived" ? (
                        <AuthoringIconAction
                          variant="warning"
                          label="Archive"
                          busy={action.busy === `archive:${version.id}`}
                          busyLabel="Archiving…"
                          disabled={action.busy !== null}
                          onClick={() =>
                            void action.run(`archive:${version.id}`, () =>
                              archiveRubricVersion(scope, data.id, version.version),
                            )
                          }
                        >
                          <HiOutlineArchiveBox className="h-4 w-4" aria-hidden />
                        </AuthoringIconAction>
                      ) : null}
                    </AuthoringRowActions>
                  </div>
                </Panel>
              ))}

          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
