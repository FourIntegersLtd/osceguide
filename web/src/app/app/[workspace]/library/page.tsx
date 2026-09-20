import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { LibraryRedirect } from "@/app/app/[workspace]/library/redirect-client";

export const metadata: Metadata = { title: "Study material" };

export default function Page() {
  return (
    <Capability id="media">
      <LibraryRedirect />
    </Capability>
  );
}
