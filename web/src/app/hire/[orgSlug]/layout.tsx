import type { ReactNode } from "react";
import { HireShell } from "@/surfaces";

export default async function HireLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ orgSlug: string }>;
}) {
  const { orgSlug } = await params;
  return <HireShell orgSlug={orgSlug}>{children}</HireShell>;
}
