"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { HiOutlineLightBulb } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { b2cBodyText, b2cReadingTones } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import { consultationToolkit } from "./consultationToolkit";

interface Activity {
  about: string;
  educationalActivity: string[];
}

const tipTone = b2cReadingTones.tip;
const practiceTone = b2cReadingTones.practice;

/** RCGP-style display labels. do not rename toolkit keys. */
const SKILL_LABELS: Record<string, string> = {
  opens_consultation: "Opens consultation",
  discovers_psychosocial_context: "Discovers psychosocial context",
  identifies_cues: "Identifies cues",
  discovers_ice: "Discovers ICE",
  interprets_tests: "Interprets tests",
  generates_hypotheses: "Generates hypotheses",
  rules_in_out_disease: "Rules in or out disease",
  reaches_diagnosis: "Reaches diagnosis",
  generates_rapport: "Generates rapport",
  uses_open_questions: "Uses open questions",
  clarifies_cues: "Clarifies cues",
  listens_curiosity: "Listens with curiosity",
  uses_closed_questions: "Uses closed questions",
  explains_rationale: "Explains rationale",
  verbalises_diagnosis: "Verbalises diagnosis",
  shares_ice_plan: "Shares ICE plan",
  negotiates_psychosocial_plan: "Negotiates psychosocial plan",
  offers_management_plan: "Offers management plan",
  manages_comorbidity: "Manages comorbidity",
  provides_safety_net: "Provides safety net",
  structures_consultation: "Structures consultation",
  avoids_repetition: "Avoids repetition",
  progresses_through_tasks: "Progresses through tasks",
  recognises_ethical_implications: "Recognises ethical implications",
  finishes_data_gathering: "Finishes data gathering",
  uses_clear_language: "Uses clear language",
  remains_responsive_to_patient: "Remains responsive to patient",
};

const CATEGORY_LABELS: Record<string, string> = {
  tasks: "Tasks",
  relatingToOthers: "Relating to others",
  clinicalManagement: "Clinical management",
  globalSkills: "Global skills",
};

function skillLabel(skillKey: string): string {
  return (
    SKILL_LABELS[skillKey] ??
    skillKey
      .split("_")
      .join(" ")
      .replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

function categoryLabel(categoryKey: string): string {
  return CATEGORY_LABELS[categoryKey] ?? categoryKey;
}

const TipContent = () => {
  const [currentTip, setCurrentTip] = useState<{
    category: string;
    skill: string;
    activity: Activity;
  } | null>(null);
  const [currentActivityIndex, setCurrentActivityIndex] = useState(0);
  const [isChanging, setIsChanging] = useState(false);

  const getRandomTip = () => {
    setIsChanging(true);
    const categories = Object.keys(consultationToolkit);
    const randomCategory =
      categories[Math.floor(Math.random() * categories.length)];
    if (!randomCategory) return;
    const skills = Object.keys(
      consultationToolkit[randomCategory as keyof typeof consultationToolkit],
    );
    const randomSkill = skills[Math.floor(Math.random() * skills.length)];
    if (!randomSkill) return;
    setTimeout(() => {
      setCurrentTip({
        category: randomCategory,
        skill: randomSkill,
        activity:
          consultationToolkit[
            randomCategory as keyof typeof consultationToolkit
          ][randomSkill]!,
      });
      setCurrentActivityIndex(0);
      setIsChanging(false);
    }, 300);
  };

  const navigateActivity = (direction: "prev" | "next") => {
    if (!currentTip) return;
    const total = currentTip.activity.educationalActivity.length;
    setCurrentActivityIndex((prev) => {
      if (direction === "prev") {
        return prev > 0 ? prev - 1 : total - 1;
      }
      return prev < total - 1 ? prev + 1 : 0;
    });
  };

  useEffect(() => {
    const timer = window.setTimeout(getRandomTip, 0);
    return () => window.clearTimeout(timer);
  }, []);

  if (!currentTip) return null;

  return (
    <motion.div
      animate={{ opacity: isChanging ? 0 : 1 }}
      transition={{ duration: 0.3 }}
      className="grid grid-cols-1 gap-3"
    >
      <section className={cn("flex flex-col rounded-osce-lg border p-4 sm:p-5", tipTone.card)}>
        <div className="flex items-start gap-3">
          <HiOutlineLightBulb className="mt-0.5 h-5 w-5 shrink-0 text-osce-accent" aria-hidden />
          <div className="min-w-0">
            <h3 className="text-osce-body font-semibold text-osce-ink-900">{skillLabel(currentTip.skill)}</h3>
            <p className="text-osce-meta text-b2c-text-muted">{categoryLabel(currentTip.category)}</p>
          </div>
        </div>
        <p className={cn("mt-3", b2cBodyText, tipTone.body)}>{currentTip.activity.about}</p>

        <div className={cn("mt-4 flex flex-col rounded-osce-lg border p-4", practiceTone.card)}>
          <div className="flex items-center justify-between gap-2">
            <p className={cn("text-osce-meta font-medium", practiceTone.title)}>Try this</p>
            <span className="text-osce-meta tabular-nums text-b2c-text-muted">
              {currentActivityIndex + 1} of {currentTip.activity.educationalActivity.length}
            </span>
          </div>
          <motion.p
            key={currentActivityIndex}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn("mt-2", b2cBodyText, practiceTone.body)}
          >
            {currentTip.activity.educationalActivity[currentActivityIndex]}
          </motion.p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button type="button" variant="secondary" size="sm" onClick={() => navigateActivity("prev")}>
              Previous
            </Button>
            <Button type="button" variant="secondary" size="sm" onClick={() => navigateActivity("next")}>
              Next
            </Button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <p className="text-osce-meta text-b2c-text-muted">Adapted from the RCGP SCA Consultation Toolkit</p>
          <Button type="button" variant="secondary" size="sm" onClick={getRandomTip}>
            Show another skill
          </Button>
        </div>
      </section>
    </motion.div>
  );
};

export default TipContent;
