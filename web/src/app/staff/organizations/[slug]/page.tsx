import type { Metadata } from "next";
import { OrganizationDetail } from "@/domains/platform";

export const metadata: Metadata = { title: "Organisation" };

/**
 * One tenant, from the staff console.
 *
 * A route file of its own rather than a screen in the arm's `ScreenMap`: that
 * map exists for pages whose meaning changes with the workspace, and the staff
 * console has no workspace. `/staff/organizations/<slug>` names an
 * organisation the way a customer's URL names theirs, without standing in it.
 */
export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <OrganizationDetail slug={slug} />;
}
