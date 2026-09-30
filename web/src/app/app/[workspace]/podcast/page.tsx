import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { MediaKindLibrary } from "@/capabilities/media/MediaKindLibrary";

export const metadata: Metadata = { title: "Podcast" };

export default function Page() {
  return (
    <Capability id="study-podcast">
      <MediaKindLibrary kind="podcast" />
    </Capability>
  );
}
