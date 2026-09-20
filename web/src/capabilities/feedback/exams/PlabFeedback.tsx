"use client";
import { LuHandshake, LuStethoscope } from "react-icons/lu";
import { HiOutlineMagnifyingGlass } from "react-icons/hi2";
import { Dropdown } from "@/foundation/table";
import type { PlabFeedbackProps } from "./plabTypes";
import { ScoreCard, getScoreColor } from "./PlabScoreCard";
import { plabSummary } from "./plabSummary";
function PlabFeedback({ feedback }: PlabFeedbackProps) {
  const { total, passed } = plabSummary(feedback);
  return (
    <div className="mx-auto w-full max-w-osce-page">
      {" "}
      <div className="mb-8">
        {" "}
        <div className="flex flex-wrap gap-2 text-osce-title items-center justify-center">
          {" "}
          Overall Score:{" "}
          <span
            className={`ml-2 font-bold ${getScoreColor(total / 12)}`}
          >
            {" "}
            {Math.round(total * 100) / 100}/12{" "}
          </span>{" "}
          <span
            className={`ml-2 font-bold px-4 py-1 rounded-full ${passed ? "bg-osce-success-bg text-osce-success-icon" : "bg-osce-danger-bg text-osce-danger"}`}
          >
            {" "}
            {passed
              ? "Passed"
              : "Failed"}{" "}
          </span>{" "}
        </div>{" "}
      </div>{" "}
      {/* Data Gathering Section */}{" "}
      <Dropdown title="Data Gathering" defaultOpen icon={<HiOutlineMagnifyingGlass className="h-5 w-5" />}>
        {" "}
        <section className="mb-12">
          {" "}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {" "}
            <ScoreCard
              title="History Taking"
              score={feedback.data_gathering.history_taking.score}
              items={feedback.data_gathering.history_taking}
            />{" "}
            <ScoreCard
              title="Examination"
              score={feedback.data_gathering.examination.score}
              items={feedback.data_gathering.examination}
            />{" "}
            <ScoreCard
              title="Investigations"
              score={feedback.data_gathering.investigations.score}
              items={feedback.data_gathering.investigations}
            />{" "}
            <ScoreCard
              title="Clinical Interpretation"
              score={feedback.data_gathering.interpretation.score}
              items={feedback.data_gathering.interpretation}
            />{" "}
          </div>{" "}
        </section>{" "}
      </Dropdown>{" "}
      {/* Clinical Management Section */}{" "}
      <Dropdown
        defaultOpen
        title="Clinical Management"
        icon={<LuStethoscope className="h-5 w-5" />}
      >
        {" "}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {" "}
          <ScoreCard
            title="Diagnosis"
            score={feedback.clinical_management.diagnosis.score}
            items={feedback.clinical_management.diagnosis}
          />{" "}
          <ScoreCard
            title="Management Plan"
            score={feedback.clinical_management.management_plan.score}
            items={feedback.clinical_management.management_plan}
          />{" "}
          <ScoreCard
            title="Safety Netting"
            score={feedback.clinical_management.safety_netting.score}
            items={feedback.clinical_management.safety_netting}
          />{" "}
          <ScoreCard
            title="Follow-up Plan"
            score={feedback.clinical_management.follow_up.score}
            items={feedback.clinical_management.follow_up}
          />{" "}
        </div>{" "}
      </Dropdown>{" "}
      {/* Interpersonal Skills Section */}{" "}
      <Dropdown
        defaultOpen
        title="Interpersonal Skills"
        icon={<LuHandshake className="h-6 w-6" />}
      >
        {" "}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {" "}
          <ScoreCard
            title="Communication"
            score={feedback.interpersonal_skills.language.score}
            items={feedback.interpersonal_skills.language}
          />{" "}
          <ScoreCard
            title="Active Listening"
            score={feedback.interpersonal_skills.listening.score}
            items={feedback.interpersonal_skills.listening}
          />{" "}
          <ScoreCard
            title="Patient Rapport"
            score={feedback.interpersonal_skills.rapport.score}
            items={feedback.interpersonal_skills.rapport}
          />{" "}
          <ScoreCard
            title="Empathy"
            score={feedback.interpersonal_skills.empathy.score}
            items={feedback.interpersonal_skills.empathy}
          />{" "}
        </div>{" "}
      </Dropdown>{" "}
    </div>
  );
}
export default PlabFeedback;
