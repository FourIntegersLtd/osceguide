export interface SubSection {
  completed: string[];
  missed: string[];
  score: number;
  supporting_phrase?: string | string[];
  suggested_actions?: string[];
  critical_flags?: string[];
}
export interface DataGatheringSection {
  history_taking: SubSection;
  examination: SubSection;
  investigations: SubSection;
  interpretation: SubSection;
}
export interface ClinicalManagementSection {
  diagnosis: SubSection;
  management_plan: SubSection;
  safety_netting: SubSection;
  follow_up: SubSection;
}
export interface InterpersonalSkillsSection {
  language: SubSection;
  listening: SubSection;
  rapport: SubSection;
  empathy: SubSection;
}
export interface PlabFeedbackData {
  data_gathering: DataGatheringSection;
  clinical_management: ClinicalManagementSection;
  interpersonal_skills: InterpersonalSkillsSection;
  passed_station?: boolean;
  feedback_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  evaluated_by: string;
  mock_id: string;
  station_id: string;
}
export interface PlabFeedbackType {
  data_gathering: {
    history_taking: PlabEvaluationScore;
    examination: PlabEvaluationScore;
    investigations: PlabEvaluationScore;
    interpretation: PlabEvaluationScore;
  };
  clinical_management: {
    diagnosis: PlabEvaluationScore;
    management_plan: PlabEvaluationScore;
    safety_netting: PlabEvaluationScore;
    follow_up: PlabEvaluationScore;
  };
  interpersonal_skills: {
    language: PlabEvaluationScore;
    listening: PlabEvaluationScore;
    rapport: PlabEvaluationScore;
    empathy: PlabEvaluationScore;
  };
  passed_station?: boolean;
  feedback_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  mock_id: string;
  station_id: string;
}
export interface PlabEvaluationScore {
  score: number;
  supporting_phrase?: string | string[];
  suggested_actions?: string[];
  critical_flags?: string[];
}
export interface PlabFeedbackProps {
  feedback: PlabFeedbackType | PlabFeedbackData;
}
