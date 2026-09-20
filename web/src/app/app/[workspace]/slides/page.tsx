import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { MediaKindLibrary } from "@/capabilities/media/MediaKindLibrary";

export const metadata: Metadata = { title: "Slides" };

export default function Page() {
  return (
    <Capability id="study-slides">
      <MediaKindLibrary kind="slide_deck" />
    </Capability>
  );
}
