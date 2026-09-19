/*
 * A capability page: the same component on every arm that mounts it.
 *
 * No per-arm variant and no branch. Which arms reach this page is `surfaces`
 * in the capability's manifest; the navigation, the href prefix and the help
 * assistant's knowledge of the section all follow from that one list.
 * `<Capability>` turns the same registry into the 404 for an arm that does not
 * mount it.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { Discussion } from "@/capabilities/community";

export const metadata: Metadata = { title: "Discussion" };

export default function Page() {
  return <Capability id="community"><Discussion /></Capability>;
}
