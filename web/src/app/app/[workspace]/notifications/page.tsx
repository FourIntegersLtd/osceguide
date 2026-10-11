import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { Inbox } from "@/capabilities/inbox";

export const metadata: Metadata = {
  title: "Notifications",
  description: "Replies and news from the OSCE Guide team.",
};

export default function Page() {
  return (
    <Capability id="inbox">
      <Inbox />
    </Capability>
  );
}
