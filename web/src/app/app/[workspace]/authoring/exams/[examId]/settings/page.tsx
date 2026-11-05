import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { ExamSettingsScreen } from "@/capabilities/authoring/exams/ExamSettingsScreen";

export const metadata: Metadata = { title: "Exam settings" };

export default async function Page({ params }: { params: Promise<{ examId: string }> }) {
  const { examId } = await params;
  return (
    <Capability id="authoring">
      <ExamSettingsScreen examId={examId} />
    </Capability>
  );
}
