/*
 * A capability page: the same component on every arm that mounts it.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { AuthoringHome } from "@/capabilities/authoring";

export const metadata: Metadata = { title: "Exams" };

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; section: string }>;
}) {
  const { section } = await params;
  return (
    <Capability id="authoring">
      <AuthoringHome section={section} />
    </Capability>
  );
}
