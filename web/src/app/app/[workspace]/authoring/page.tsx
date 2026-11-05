import { redirect } from "next/navigation";

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string }>;
}) {
  const { workspace } = await params;
  redirect(`/app/${workspace}/authoring/exams`);
}
