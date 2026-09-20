import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { MediaKindLibrary } from "@/capabilities/media/MediaKindLibrary";

export const metadata: Metadata = { title: "A to Z" };

export default function Page() {
  return (
    <Capability id="study-a-to-z">
      <MediaKindLibrary kind="summary" />
    </Capability>
  );
}
