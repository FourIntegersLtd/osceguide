import type { Metadata } from "next";
import { AuthoringHome } from "@/capabilities/authoring";

export const metadata: Metadata = { title: "Authoring" };

export default async function Page({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  return <AuthoringHome section={section} />;
}
