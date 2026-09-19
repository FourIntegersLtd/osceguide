import type { Metadata } from "next";
import { MediaLibrary } from "@/capabilities/media";

export const metadata: Metadata = { title: "Study material" };

export default function LibraryPage() {
  return <MediaLibrary />;
}
