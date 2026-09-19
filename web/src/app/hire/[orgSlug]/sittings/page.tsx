import type { Metadata } from "next";
import { Sittings } from "@/domains/assess";

export const metadata: Metadata = { title: "Assessments" };

export default async function HireSittingsPage({
  params,
}: {
  params: Promise<{ orgSlug: string }>;
}) {
  const { orgSlug } = await params;
  return <Sittings orgSlug={orgSlug} />;
}
