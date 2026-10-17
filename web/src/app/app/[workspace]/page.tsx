"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { PageSpinner } from "@/foundation/ui";
import { workspaceBasePath } from "@/foundation/routing";

/**
 * A workspace with no page named: go to its landing screen.
 *
 * Every arm declares a `dashboard`, and its manifest decides what that is, so
 * this needs to know nothing about which arm it is sending anybody to. The
 * base path comes from `foundation/routing` rather than being spelled here —
 * that module owns the grammar, and this page is not the place to repeat it.
 */
export default function WorkspaceIndex() {
  const { workspace } = useParams<{ workspace: string }>();
  const router = useRouter();

  useEffect(() => {
    if (workspace) router.replace(`${workspaceBasePath(workspace)}/dashboard`);
  }, [workspace, router]);

  return (
    <PageSpinner fill="section" />
  );
}
