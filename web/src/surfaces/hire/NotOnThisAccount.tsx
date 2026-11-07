"use client";

import Link from "next/link";
import { boardBtn, boardCard } from "@/foundation/ui/boardKit";
import { can, useSession } from "@/foundation/session";
import { workspaceBasePath, type Workspace } from "@/foundation/routing";

/**
 * HireRefused: the learner's pages (self practice, practice sessions) asked of an employer's workspace.
 * The hire surface leaves them out of its screen list, so the route lands here without calling the api;
 * staff are sent to the overview, a candidate to their own assessments.
 */
export function NotOnThisAccount({ workspace }: { workspace: Workspace }) {
  const { session } = useSession();
  const staff = can(session, "run_circuits");
  const base = workspaceBasePath(workspace);
  return (
    <section aria-label="Not on this account" className={boardCard}>
      <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
        <h1 className="text-base font-semibold leading-normal text-osce-ink-900">This is not part of your employer&apos;s account</h1>
        <p className="m-0 max-w-sm text-assess-label text-osce-ink-700">
          {`Practice stations and mock exams are not included with ${workspace.name}. ${staff ? "Your overview is" : "Your assessments are"} on your home page.`}
        </p>
        <Link href={`${base}${staff ? "/dashboard" : "/trainee"}`} className={boardBtn("primary")}>
          {staff ? "Go to the overview" : "Go to my assessments"}
        </Link>
      </div>
    </section>
  );
}
