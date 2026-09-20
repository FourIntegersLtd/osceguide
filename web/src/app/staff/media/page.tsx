import type { Metadata } from "next";
import { Suspense } from "react";
import { MediaAuthoringHome } from "@/capabilities/staff-media/MediaAuthoringHome";

export const metadata: Metadata = { title: "Study material" };

export default function Page() {
  return (
    <Suspense fallback={null}>
      <MediaAuthoringHome />
    </Suspense>
  );
}
