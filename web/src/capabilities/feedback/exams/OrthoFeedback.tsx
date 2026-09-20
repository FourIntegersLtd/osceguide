"use client";
import { useState } from "react";
import type { OrthoFeedbackType } from "./orthoTypes";
import { b2cStatValue } from "@/foundation/ui/productTokens";
import { clinicalCompetencyDescriptions, prioritisationCompetencyDescriptions, communicationCompetencyDescriptions, portfolioCompetencyDescriptions } from "./orthoCompetencies";
import { ScoreCard } from "./OrthoScoreCard";
const formatApiUtcLocaleDateString = (value: string) => value ? new Date(value).toLocaleDateString() : "";
const StationTypeHeader = ({ stationType }: { stationType: string }) => {
  const getStationTitle = () => {
    switch (stationType) {
      case "clinical":
        return "Clinical Skills";
      case "prioritisation":
        return "Prioritisation";
      case "communication":
        return "Communication";
      case "portfolio":
        return "Portfolio";
      default:
        return "Station";
    }
  };
  return (
    <div className="text-center lg:text-left">
      {" "}
      <span className="text-osce-body text-b2c-text-muted uppercase tracking-wide">
        {" "}
        {getStationTitle()} Station{" "}
      </span>{" "}
    </div>
  );
};
function OrthoFeedback({ feedback }: { feedback: OrthoFeedbackType }) {
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());
  const toggleCard = (key: string) => {
    setExpandedCards((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };
  const getCompetencyDescriptions = () => {
    switch (feedback.station_type) {
      case "clinical":
        return clinicalCompetencyDescriptions;
      case "prioritisation":
        return prioritisationCompetencyDescriptions;
      case "communication":
        return communicationCompetencyDescriptions;
      case "portfolio":
        return portfolioCompetencyDescriptions;
      default:
        return {};
    }
  };
  const getStationSkills = () => {
    switch (feedback.station_type) {
      case "clinical":
        return feedback.clinical_skills;
      case "prioritisation":
        return feedback.prioritisation_skills;
      case "communication":
        return feedback.communication_skills;
      case "portfolio":
        return feedback.portfolio_skills;
      default:
        return null;
    }
  };
  const skills = getStationSkills();
  const descriptions = getCompetencyDescriptions();
  if (!skills) {
    return (
      <div className="text-center py-12">
        {" "}
        <p className="text-b2c-text-muted">
          No feedback available for this station.
        </p>{" "}
      </div>
    );
  }
  const percentage = ((feedback.station_total || 0) / 50) * 100;
  return (
    <div className="w-full space-y-6">
      {" "}
      {/* Header with Station Type and Score */}{" "}
      <div className="flex flex-col gap-4 pb-4 border-b border-b2c-border lg:flex-row lg:items-center lg:justify-between">
        {" "}
        <StationTypeHeader stationType={feedback.station_type} />{" "}
        {/* Overall Score - Responsive Layout */}{" "}
        <div className="flex flex-col gap-4 w-full lg:w-auto lg:flex-row lg:items-center lg:gap-8">
          {" "}
          {/* Legend: total score out of 50 (pass = 35) */}{" "}
          <div className="flex items-center justify-between gap-2 text-osce-caption text-b2c-text-muted w-full lg:w-auto lg:gap-4">
            {" "}
            <span className="flex items-center gap-1">
              0-17 <span className="text-osce-danger">●</span>
            </span>{" "}
            <span className="flex items-center gap-1">
              18-34 <span className="text-osce-warning-text">●</span>
            </span>{" "}
            <span className="flex items-center gap-1">
              35-42 <span className="text-osce-accent">●</span>
            </span>{" "}
            <span className="flex items-center gap-1">
              43-50 <span className="text-osce-success-text">●</span>
            </span>{" "}
          </div>{" "}
          {/* Score - Full width on mobile, bordered on desktop */}{" "}
          <div className="flex items-center justify-center gap-4 w-full lg:justify-start lg:w-auto lg:border-l lg:border-b2c-border lg:pl-8">
            {" "}
            <div
              className={`${b2cStatValue} font-bold ${percentage >= 70 ? "text-osce-success-text" : "text-osce-danger"}`}
            >
              {" "}
              {feedback.station_total || 0}{" "}
            </div>{" "}
            <div className="text-left">
              {" "}
              <div className="text-osce-body text-b2c-text-muted">
                out of 50
              </div>{" "}
              <div
                className={`text-osce-body font-medium ${percentage >= 70 ? "text-osce-success-text" : "text-osce-danger"}`}
              >
                {" "}
                {percentage.toFixed(0)}% {percentage >= 70 ? "✓" : "✗"}{" "}
              </div>{" "}
            </div>{" "}
          </div>{" "}
        </div>{" "}
      </div>{" "}
      {/* Competencies - Full Width */}{" "}
      <div className="space-y-3">
        {" "}
        {Object.entries(skills).map(([key, value]) => {
          const description = descriptions[key];
          return (
            <ScoreCard
              key={key}
              title={
                description?.title ||
                key
                  .replace(/_/g, " ")
                  .split(" ")
                  .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(" ")
              }
              score={value.score}
              description={description?.description || ""}
              items={value}
              isExpanded={expandedCards.has(key)}
              onToggle={() => toggleCard(key)}
            />
          );
        })}{" "}
      </div>{" "}
      {/* Metadata - Minimal */}{" "}
      <div className="text-right text-osce-caption text-b2c-text-muted pt-4">
        {" "}
        {formatApiUtcLocaleDateString(feedback.created_at)}{" "}
      </div>{" "}
    </div>
  );
}
export default OrthoFeedback;
