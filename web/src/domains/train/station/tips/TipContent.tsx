"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { AthenaIdentity } from "@/foundation/ui";
import {
  ModalContent,
  ModalPrimaryButton,
  ModalSecondaryButton,
} from "@/foundation/ui";
import {
  B2CPanelCard,
  B2CPanelCardHeader,
  B2CPanelCardBody,
  B2CPanelCardFooter,
} from "@/foundation/ui";
import { b2cBodyText, b2cBodyTextMuted, b2cReadingTones } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import { consultationToolkit } from "./consultationToolkit";

interface Activity {
  about: string;
  educationalActivity: string[];
}

interface TipContentProps {
  width?: string;
}

const tipTone = b2cReadingTones.tip;
const practiceTone = b2cReadingTones.practice;

/** RCGP-style display labels. do not rename toolkit keys. */
const SKILL_LABELS: Record<string, string> = {
  opens_consultation: "Opens Consultation",
  discovers_psychosocial_context: "Discovers Psychosocial Context",
  identifies_cues: "Identifies Cues",
  discovers_ice: "Discovers ICE",
  interprets_tests: "Interprets Tests",
  generates_hypotheses: "Generates Hypotheses",
  rules_in_out_disease: "Rules In/Out Disease",
  reaches_diagnosis: "Reaches Diagnosis",
  generates_rapport: "Generates Rapport",
  uses_open_questions: "Uses Open Questions",
  clarifies_cues: "Clarifies Cues",
  listens_curiosity: "Listens with Curiosity",
  uses_closed_questions: "Uses Closed Questions",
  explains_rationale: "Explains Rationale",
  verbalises_diagnosis: "Verbalises Diagnosis",
  shares_ice_plan: "Shares ICE Plan",
  negotiates_psychosocial_plan: "Negotiates Psychosocial Plan",
  offers_management_plan: "Offers Management Plan",
  manages_comorbidity: "Manages Comorbidity",
  provides_safety_net: "Provides Safety Net",
  structures_consultation: "Structures Consultation",
  avoids_repetition: "Avoids Repetition",
  progresses_through_tasks: "Progresses Through Tasks",
  recognises_ethical_implications: "Recognises Ethical Implications",
  finishes_data_gathering: "Finishes Data Gathering",
  uses_clear_language: "Uses Clear Language",
  remains_responsive_to_patient: "Remains Responsive to Patient",
};

const CATEGORY_LABELS: Record<string, string> = {
  tasks: "Tasks",
  relatingToOthers: "Relating to Others",
  clinicalManagement: "Clinical Management",
  globalSkills: "Global Skills",
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

const TipContent: React.FC<TipContentProps> = ({ width = "w-full" }) => {
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
    <ModalContent className={`mb-24 max-w-2xl space-y-3 lg:${width}`}>
      <motion.div
        animate={{ opacity: isChanging ? 0 : 1 }}
        transition={{ duration: 0.3 }}
        className="space-y-3"
      >
        <B2CPanelCard className={`mt-0 ${tipTone.card}`}>
          <B2CPanelCardHeader className={tipTone.header}>
            Consultation tip
          </B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-4">
            <AthenaIdentity
              layout="inline"
              title={skillLabel(currentTip.skill)}
              description={categoryLabel(currentTip.category)}
            />

            <p className={cn(b2cBodyText, tipTone.body)}>
              {currentTip.activity.about}
            </p>
            <p className={b2cBodyTextMuted}>
              Adapted from the RCGP SCA Consultation Toolkit
            </p>
          </B2CPanelCardBody>
        </B2CPanelCard>

        <B2CPanelCard className={`mt-0 ${practiceTone.card}`}>
          <B2CPanelCardHeader className={practiceTone.header}>
            Try this
          </B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-4">
            <motion.p
              key={currentActivityIndex}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(b2cBodyText, practiceTone.body)}
            >
              {currentTip.activity.educationalActivity[currentActivityIndex]}
            </motion.p>

            <div className="flex items-center justify-between gap-2 border-t border-osce-warning-border/60 pt-3">
              <ModalSecondaryButton
                type="button"
                onClick={() => navigateActivity("prev")}
                className="min-h-9 px-3"
              >
                Previous
              </ModalSecondaryButton>
              <span className={b2cBodyTextMuted}>
                {currentActivityIndex + 1} of{" "}
                {currentTip.activity.educationalActivity.length}
              </span>
              <ModalSecondaryButton
                type="button"
                onClick={() => navigateActivity("next")}
                className="min-h-9 px-3"
              >
                Next
              </ModalSecondaryButton>
            </div>
          </B2CPanelCardBody>
          <B2CPanelCardFooter>
            <ModalPrimaryButton type="button" onClick={getRandomTip}>
              Show another skill
            </ModalPrimaryButton>
          </B2CPanelCardFooter>
        </B2CPanelCard>
      </motion.div>
    </ModalContent>
  );
};

export default TipContent;
