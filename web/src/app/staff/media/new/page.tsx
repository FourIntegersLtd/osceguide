import { redirect } from "next/navigation";
import { isMediaKind } from "@/capabilities/media/api";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ kind?: string }>;
}) {
  const { kind: raw } = await searchParams;
  const kind = raw && isMediaKind(raw) ? raw : "summary";
  redirect(`/staff/media?new=1&kind=${encodeURIComponent(kind)}`);
}
