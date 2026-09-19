/*
 * A capability page: the same component on every arm that mounts it.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { Achievements } from "@/capabilities/account";

export const metadata: Metadata = { title: "Achievements" };

export default function Page() {
  return (
    <Capability id="account">
      <Achievements />
    </Capability>
  );
}
