/*
 * A capability page: the same component on every arm that mounts it.
 *
 * No per-arm variant and no branch. Which arms reach this page is `surfaces`
 * in the capability's manifest; the navigation, the href prefix and the help
 * assistant's knowledge of the section all follow from that one list.
 * `<Capability>` turns the same registry into the 404 for an arm that does not
 * mount it.
 */

import { Capability } from "@/app/app/[workspace]/capability";
import { TranscriptDetail } from "@/capabilities/transcripts";

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; id: string }>;
}) {
  const { id } = await params;
  return <Capability id="transcripts"><TranscriptDetail id={id} /></Capability>;
}
