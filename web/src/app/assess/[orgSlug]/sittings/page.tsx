import type { Metadata } from "next";
import { Sittings } from "@/domains/assess";

export const metadata: Metadata = { title: "Sittings" };

export default async function SittingsPage({ params }: { params: Promise<{ orgSlug: string }> }) {
  const { orgSlug } = await params;
  return <Sittings orgSlug={orgSlug} />;
}
