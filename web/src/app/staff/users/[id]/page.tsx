import type { Metadata } from "next";
import { UserDetail } from "@/domains/platform";

export const metadata: Metadata = { title: "User" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <UserDetail userId={id} />;
}
