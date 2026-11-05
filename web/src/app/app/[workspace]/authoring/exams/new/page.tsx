import type { Metadata } from "next";
import { Suspense } from "react";
import { Capability } from "@/app/app/[workspace]/capability";
import { NewExamSheet } from "@/capabilities/authoring/exams/NewExamSheet";

export const metadata: Metadata = { title: "New exam" };

export default function Page() {
  return (
    <Capability id="authoring">
      <Suspense fallback={null}>
        <NewExamSheet />
      </Suspense>
    </Capability>
  );
}
