import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { Inbox } from "@/capabilities/inbox";

export const metadata: Metadata = {
  title: "Inbox",
  description: "Messages and announcements from the OSCE Guide team.",
};

export default function Page() {
  return (
    <Capability id="inbox">
      <Inbox />
    </Capability>
  );
}
