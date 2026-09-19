import type { ReactNode } from "react";
import { AssessShell } from "@/surfaces";

export default async function AssessLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ orgSlug: string }>;
}) {
  const { orgSlug } = await params;
  return <AssessShell orgSlug={orgSlug}>{children}</AssessShell>;
}
