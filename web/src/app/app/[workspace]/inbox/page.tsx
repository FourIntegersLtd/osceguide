import { redirect } from "next/navigation";

/** The inbox is Notifications now; old links and bookmarks land there. */
export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string }>;
}) {
  const { workspace } = await params;
  redirect(`/app/${workspace}/notifications`);
}
