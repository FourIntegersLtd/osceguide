import { Screen } from "@/app/app/[workspace]/screen";

/**
 * A library station, sat on its own.
 *
 * An arm-owned screen rather than part of the station library capability,
 * because what happens when you sit one differs by arm: a consumer runs the
 * four-step station screen, an institution's trainee runs self practice.
 */
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ workspace: string; stationId: string }>;
  searchParams: Promise<{ action?: string; tab?: string; attempt?: string }>;
}) {
  const { workspace, stationId } = await params;
  const { action, tab, attempt } = await searchParams;
  return (
    <Screen
      name="practiceStation"
      slug={workspace}
      params={{ stationId, action: action ?? "", tab: tab ?? "", attempt: attempt ?? "" }}
    />
  );
}
