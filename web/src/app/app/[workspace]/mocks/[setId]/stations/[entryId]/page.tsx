import { Screen } from "@/app/app/[workspace]/screen";

/**
 * One station of a practice session.
 *
 * The query string carries where in the station somebody is — sitting it or
 * reviewing it, which step, and which past attempt — so the four steps are one
 * URL rather than four routes. That is the retiring client's shape and it is
 * what makes "Review Last Attempt" a link.
 */
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ workspace: string; setId: string; entryId: string }>;
  searchParams: Promise<{ action?: string; tab?: string; attempt?: string }>;
}) {
  const { workspace, setId, entryId } = await params;
  const { action, tab, attempt } = await searchParams;
  return (
    <Screen
      name="mockStation"
      slug={workspace}
      params={{ setId, entryId, action: action ?? "", tab: tab ?? "", attempt: attempt ?? "" }}
    />
  );
}
