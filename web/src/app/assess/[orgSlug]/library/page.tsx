import type { Metadata } from "next";
import { MediaLibrary } from "@/capabilities/media";

export const metadata: Metadata = { title: "Study material" };

/**
 * The same study library consumers get.
 *
 * This file is the entire cost of "institutions want the slides and summaries
 * too": the capability is listed for `assess` in the registry, and this mounts
 * it. Nothing was ported, and there is no second implementation to keep in step.
 */
export default function OrgLibraryPage() {
  return <MediaLibrary />;
}
