import type { Metadata } from "next";
import { MessagesInbox } from "@/domains/platform";

export const metadata: Metadata = { title: "Messages" };

export default function Page() {
  return <MessagesInbox />;
}
