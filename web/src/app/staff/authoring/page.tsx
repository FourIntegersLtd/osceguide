import type { Metadata } from "next";
import { AuthoringHome } from "@/capabilities/authoring";

export const metadata: Metadata = { title: "Authoring" };

/**
 * The platform's own catalogue.
 *
 * The same component an institution and a partner get at
 * `/app/<workspace>/authoring`. It takes its scope from the surface context,
 * and the staff console's context has no organisation — so it writes against
 * `/api/v1/platform/…` instead of `/api/v1/orgs/{slug}/…` without this route,
 * or the component, knowing which arm is asking.
 *
 * No `<Capability>` wrapper: the staff layout already gates on
 * `administer_platform`, which is a stronger check than the capability's own.
 */
export default function Page() {
  return <AuthoringHome />;
}
