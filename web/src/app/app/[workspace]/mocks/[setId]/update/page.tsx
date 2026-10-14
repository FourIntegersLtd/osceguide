import { redirect } from "next/navigation";
// import { Screen } from "@/app/app/[workspace]/screen";

// Hidden for learners: only admins edit or delete sessions (2026-10-14).
// The edit screen (`mockUpdate`) stays wired; this route sends learners to the session's detail page.
export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; setId: string }>;
}) {
  const { workspace, setId } = await params;
  redirect(`/app/${workspace}/mocks/${setId}`);
  // return <Screen name="mockUpdate" slug={workspace} params={{ setId }} />;
}
