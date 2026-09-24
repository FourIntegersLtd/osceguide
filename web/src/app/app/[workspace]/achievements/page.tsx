/*
 * A capability page: the same component on every arm that mounts it.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { AchievementsLive } from "@/capabilities/account/AchievementsLive";

export const metadata: Metadata = { title: "Achievements" };

export default function Page() {
  return (
    <Capability id="achievements">
      <AchievementsLive />
    </Capability>
  );
}
