import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { ExamDetail } from "@/capabilities/authoring/exams/ExamDetail";

export const metadata: Metadata = { title: "Exam" };

export default async function Page({ params }: { params: Promise<{ examId: string }> }) {
  const { examId } = await params;
  return (
    <Capability id="authoring">
      <ExamDetail examId={examId} />
    </Capability>
  );
}
