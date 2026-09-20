export interface ImprovementModel {
  improvement: string;
  issue: string;
}
export interface StrengthModel {
  strength: string;
  example: string;
}
export interface DomainFeedback {
  strengths: StrengthModel[];
  improvements: ImprovementModel[];
  suggested_actions: string[];
}
export interface CascFeedback {
  history: {
    identifies_priorities: { competent: boolean };
    recognizes_significance: { competent: boolean };
    explores_symptoms: { competent: boolean };
    assesses_risk: { competent: boolean };
    explores_physical_health: { competent: boolean };
    identifies_psychosocial: { competent: boolean };
    generic_domains: DomainFeedback;
  };
  examination: {
    identifies_findings: { competent: boolean };
    recognizes_implications: { competent: boolean };
    examination_competence: { competent: boolean };
    formulates_diagnosis: { competent: boolean };
    generic_domains: DomainFeedback;
  };
  management: {
    problem_formulation: { competent: boolean };
    management_plan: { competent: boolean };
    risk_management: { competent: boolean };
    psychosocial_interventions: { competent: boolean };
    generic_domains: DomainFeedback;
  };
  communication: {
    consultation_structure: { competent: boolean };
    consultation_style: { competent: boolean };
    professional_behavior: { competent: boolean };
    listening_skills: { competent: boolean };
    questioning_technique: { competent: boolean };
    language_use: { competent: boolean };
    generic_domains: DomainFeedback;
  };
}
