import type { Metadata } from "next";
import { Settings } from "@/capabilities/account";

export const metadata: Metadata = { title: "Settings" };

/**
 * OSCE Guide's own staff have accounts too.
 *
 * The account capability mounts on every arm, and the staff console is the one
 * that is not a workspace — so it needs its own route rather than sharing
 * `/app/<workspace>/settings`. Without it the navigation offered a link to a
 * 404, which is how the old client ended up with a supervisor who could not
 * change their own password.
 */
export default function Page() {
  return <Settings />;
}
