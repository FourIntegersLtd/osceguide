import { OrgDashboard } from "@/domains/assess";

export default async function OrgPage({ params }: { params: Promise<{ orgSlug: string }> }) {
  const { orgSlug } = await params;
  return <OrgDashboard orgSlug={orgSlug} />;
}
