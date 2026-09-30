/*
 * Contact & Feedback — the retiring client's `/messages`, which the redirect
 * table in `foundation/routing/legacyRedirects.ts` already sends here.
 *
 * Mounted through the `messages` capability: the old client kept it on the
 * consumer arm only, so the registry is what decides where it answers.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { Messages } from "@/capabilities/help";

export const metadata: Metadata = {
  title: "Contact us",
  description: "Send a message to the OSCE Guide team.",
};

export default function Page() {
  return (
    <Capability id="messages">
      <Messages />
    </Capability>
  );
}
