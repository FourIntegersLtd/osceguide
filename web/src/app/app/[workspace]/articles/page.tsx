import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { MediaKindLibrary } from "@/capabilities/media/MediaKindLibrary";

export const metadata: Metadata = { title: "Articles" };

export default function Page() {
  return (
    <Capability id="study-articles">
      <MediaKindLibrary kind="blog" />
    </Capability>
  );
}
