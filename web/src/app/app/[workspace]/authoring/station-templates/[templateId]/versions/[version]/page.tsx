import type { Metadata } from "next";
import { StationTemplateEditScreen } from "@/capabilities/authoring/templates/StationTemplateEditScreen";

export const metadata: Metadata = { title: "Edit station template" };

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; templateId: string; version: string }>;
}) {
  const { templateId, version } = await params;
  const versionNumber = Number.parseInt(version, 10);
  return (
    <StationTemplateEditScreen
      templateId={templateId}
      version={Number.isFinite(versionNumber) ? versionNumber : 0}
    />
  );
}
