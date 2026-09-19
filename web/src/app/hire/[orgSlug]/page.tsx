import { OrgDashboard } from "@/domains/assess";

/**
 * Hiring's overview is Assess's.
 *
 * An employer is an organisation running exam-mode sittings, so the read model
 * is the same one. This route exists for the surface and its skin, not for a
 * second implementation — which is the property ADR 0001 set out to protect.
 */
export default async function HirePage({ params }: { params: Promise<{ orgSlug: string }> }) {
  const { orgSlug } = await params;
  return <OrgDashboard orgSlug={orgSlug} />;
}
