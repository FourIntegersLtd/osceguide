import type { Metadata } from "next";
import { RubricBuilderScreen } from "@/capabilities/authoring/rubrics/RubricBuilderScreen";
import { RubricDashboardPreview } from "@/domains/train/dashboard/RubricDashboardPreview";

export const metadata: Metadata = { title: "Edit marking scheme" };

// The dashboard preview is the learner dashboard's own cards, which live in a
// domain; the route is the tier allowed to hand them to the capability.
export default async function Page({ params }: { params: Promise<{ rubricId: string; version: string }> }) {
  const { rubricId, version } = await params;
  const versionNumber = Number.parseInt(version, 10);
  return (
    <RubricBuilderScreen
      rubricId={rubricId}
      version={Number.isFinite(versionNumber) ? versionNumber : 0}
      dashboardPreview={RubricDashboardPreview}
    />
  );
}
