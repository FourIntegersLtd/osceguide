export interface OrthoEvaluationScore {
  score: number;
  score_justification: string;
  evidence_points: string[];
  completed: string[];
  suggested_actions: string[];
} // Clinical Station (Station 2)
export interface OrthoClinicalSkills {
  technical_knowledge_clinical_expertise: OrthoEvaluationScore;
  situational_awareness: OrthoEvaluationScore;
  communication_information_gathering: OrthoEvaluationScore;
  problem_solving_decision_making: OrthoEvaluationScore;
  communication_information_giving: OrthoEvaluationScore;
} // Prioritisation Station (Station 3)
export interface OrthoPrioritisationSkills {
  organisation_planning: OrthoEvaluationScore;
  judgement_under_pressure: OrthoEvaluationScore;
  situational_awareness: OrthoEvaluationScore;
  problem_solving_decision_making: OrthoEvaluationScore;
  communication_information_gathering: OrthoEvaluationScore;
} // Communication Station (Station 4)
export interface OrthoCommunicationSkills {
  communication_information_gathering: OrthoEvaluationScore;
  communication_information_giving: OrthoEvaluationScore;
  situational_awareness: OrthoEvaluationScore;
  judgement_under_pressure: OrthoEvaluationScore;
  technical_knowledge_clinical_expertise: OrthoEvaluationScore;
} // Portfolio Station
export interface OrthoPortfolioSkills {
  person_specifications_cv_articulation: OrthoEvaluationScore;
  portfolio_knowledge: OrthoEvaluationScore;
  reflection_professional_conduct: OrthoEvaluationScore;
  communication_information_giving: OrthoEvaluationScore;
  critical_thinking_justification: OrthoEvaluationScore;
}
export interface OrthoFeedbackType {
  feedback_id: string;
  user_id: string;
  created_at: string;
  updated_at: string | null;
  evaluated_by: string;
  mock_id: string;
  station_id: string;
  station_type: "clinical" | "prioritisation" | "communication" | "portfolio";
  clinical_skills?: OrthoClinicalSkills;
  prioritisation_skills?: OrthoPrioritisationSkills;
  communication_skills?: OrthoCommunicationSkills;
  portfolio_skills?: OrthoPortfolioSkills;
  station_total?: number;
  passed_station?: boolean;
}
