import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { RubricBuilderScreen } from "@/capabilities/authoring/rubrics/RubricBuilderScreen";
import { RubricDashboardPreview } from "@/domains/train/dashboard/RubricDashboardPreview";

export const metadata: Metadata = { title: "Edit rubric" };

// The dashboard preview is the learner dashboard's own cards, which live in a
// domain; the route is the tier allowed to hand them to the capability.
export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; rubricId: string; version: string }>;
}) {
  const { rubricId, version } = await params;
  const versionNumber = Number.parseInt(version, 10);
  return (
    <Capability id="authoring">
      <RubricBuilderScreen
        rubricId={rubricId}
        version={Number.isFinite(versionNumber) ? versionNumber : 0}
        dashboardPreview={RubricDashboardPreview}
      />
    </Capability>
  );
}
