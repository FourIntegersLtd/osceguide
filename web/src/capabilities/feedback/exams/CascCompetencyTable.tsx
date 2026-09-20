import { HiOutlineCheckCircle, HiOutlineXCircle } from "react-icons/hi2";
import { b2cTableCell, b2cTableHeader } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui";
interface CompetencyDescription {
  title: string;
  description: string;
  failureCriteria: string;
}
const competencyDescriptions: Record<string, CompetencyDescription> = {
  // History Taking Competencies identifies_priorities: { title: "Identification & Prioritization of Issues", description: "Identifies and prioritizes key presenting issues clearly, maintains structured history taking, recognizes urgent concerns", failureCriteria: "Does not identify issues or priorities. Consultation appears disorganized/unstructured with poor management.", }, recognizes_significance: { title: "Recognition of Clinical Significance", description: "Recognizes clinical significance of symptoms, makes appropriate connections, shows clear clinical reasoning", failureCriteria: "Fails to recognize significance of aspects of history. Does not make appropriate clinical connections.", }, explores_symptoms: { title: "Symptom Exploration", description: "Elicits and explores symptoms in appropriate detail, maintains comprehensive history taking", failureCriteria: "Does not elicit or explore relevant symptoms/details in sufficient detail. History taking appears superficial.", }, assesses_risk: { title: "Risk Assessment", description: "Conducts thorough risk assessment, explores risk factors, establishes current risk level", failureCriteria: "Does not demonstrate adequate skills in risk assessment. Fails to identify or explore important risk factors.", }, explores_physical_health: { title: "Physical Health Assessment", description: "Pays appropriate attention to physical health, medication effects, and monitoring needs", failureCriteria: "Does not pay sufficient attention to patient's physical health/views, including medication effects.", }, identifies_psychosocial: { title: "Psychosocial Assessment", description: "Gathers appropriate psychological and social information, explores context and support systems", failureCriteria: "Does not identify appropriate psychological or social information. Poor exploration of context.", }, // Examination Competencies identifies_findings: { title: "Identification of Clinical Findings", description: "Accurately identifies abnormal mental state findings and objective signs", failureCriteria: "Does not identify abnormal findings/results. Poor observation of mental state signs.", }, recognizes_implications: { title: "Recognition of Clinical Implications", description: "Recognizes significance of findings and links to diagnostic criteria", failureCriteria: "Fails to recognize significance or implications of findings. Poor clinical interpretation.", }, examination_competence: { title: "Examination Technique", description: "Conducts systematic mental state examination with appropriate use of cognitive testing", failureCriteria: "Does not explore symptoms and signs competently. Examination lacks structure or completeness.", }, formulates_diagnosis: { title: "Diagnostic Formulation", description: "Generates appropriate psychiatric differential diagnoses and identifies comorbidities", failureCriteria: "Does not make correct diagnosis or formulate the problem effectively. Poor diagnostic reasoning.", }, // Management Competencies problem_formulation: { title: "Problem Formulation", description: "Formulates problems effectively with clear synthesis of information", failureCriteria: "Does not formulate problem effectively. Poor integration of clinical information.", }, management_plan: { title: "Management Planning", description: "Develops comprehensive management plan reflecting current best practice", failureCriteria: "Does not develop adequate management plan that reflects knowledge of current best practice.", }, risk_management: { title: "Risk Management", description: "Develops comprehensive risk management plan with appropriate safety measures", failureCriteria: "Does not develop adequate risk management plan. Plan does not reflect risks of different management options.", }, psychosocial_interventions: { title: "Psychosocial Interventions", description: "Identifies appropriate psychological and social interventions with holistic approach", failureCriteria: "Does not identify appropriate psychological or social interventions. Limited scope of interventions.", }, // Communication Competencies consultation_structure: { title: "Consultation Structure", description: "Maintains organized consultation with effective flow and progression", failureCriteria: "Disorganized/unstructured consultation. Poor management of consultation flow.", }, consultation_style: { title: "Consultation Style", description: "Demonstrates empathic, non-judgmental approach with appropriate boundaries", failureCriteria: "Consultation appears formulaic. Does not show appropriate therapeutic engagement.", }, professional_behavior: { title: "Professional Behavior", description: "Shows appropriate professional attitude and cultural sensitivity", failureCriteria: "Does not show appropriate attitude or behavior. Poor professional boundaries.", }, listening_skills: { title: "Listening Skills", description: "Demonstrates active listening with appropriate response to verbal/non-verbal cues", failureCriteria: "Poor listening skills. Poor use and response to cues. Does not demonstrate active listening.", }, questioning_technique: { title: "Questioning Technique", description: "Uses appropriate questioning style with balance of open and closed questions", failureCriteria: "Poor questioning style. Questions appear formulaic or inappropriate.", }, language_use: { title: "Language Use", description: "Uses appropriate language, avoids jargon, adapts to patient's level", failureCriteria: "Poor use of language in context of scenario. Inappropriate terminology or jargon.", },
};
/**
 * Each CASC domain has its own concrete key set, so the shared renderers take
 * the domain as a plain object and skip whatever is not a competency row.
 */
export const asCompetency = (value: unknown): { competent: boolean } | null =>
  value && typeof value === "object" && "competent" in value
    ? { competent: Boolean((value as { competent: unknown }).competent) }
    : null;

export const domainEntries = (data: object): [string, unknown][] =>
  Object.entries(data as Record<string, unknown>);

export const CompetencyTable = ({
  scores,
  title,
}: {
  scores: object;
  title: string;
}) => {
  return (
    <div className="min-w-0 max-w-full space-y-3">
      {title ? (
        <h3 className="text-osce-body font-medium text-b2c-text-secondary">{title}</h3>
      ) : null}
      <table data-b2c-table="" className="w-full">
        {" "}
        <thead>
          {" "}
          <tr className="border-b border-b2c-border">
            {" "}
            <th className={`py-2 text-left ${b2cTableHeader}`}>Competency</th>{" "}
            <th className={`w-24 py-2 text-center ${b2cTableHeader}`}>Status</th>{" "}
          </tr>{" "}
        </thead>{" "}
        <tbody>
          {" "}
          {domainEntries(scores).map(([key, rawValue]) => {
            const value = asCompetency(rawValue);
            if (key !== "generic_domains" && value) {
              const description = competencyDescriptions[key];
              return (
                <tr key={key} className="border-b border-b2c-border group relative">
                  {" "}
                  <td className={cn("py-2", b2cTableCell)}>
                    {" "}
                    <div className="cursor-help">
                      {" "}
                      {description?.title ||
                        key
                          .replace(/_/g, " ")
                          .split(" ")
                          .map(
                            (word) =>
                              word.charAt(0).toUpperCase() + word.slice(1),
                          )
                          .join(" ")}{" "}
                      {/* Tooltip */}{" "}
                      <div className="invisible group-hover:visible absolute z-10 w-80 bg-b2c-secondary text-white text-osce-body rounded-lg p-3 -mt-1 ml-4">
                        {" "}
                        <p className="font-semibold mb-1">
                          {" "}
                          {description?.description}{" "}
                        </p>{" "}
                        {!value.competent && (
                          <p className="text-osce-danger mt-2">
                            {" "}
                            Failure criteria:{" "}
                            {description?.failureCriteria}{" "}
                          </p>
                        )}{" "}
                      </div>{" "}
                    </div>{" "}
                  </td>{" "}
                  <td className={cn("text-center", b2cTableCell)}>
                    {" "}
                    {value.competent ? (
                      <HiOutlineCheckCircle className="text-osce-success-icon h-5 w-5 inline" />
                    ) : (
                      <HiOutlineXCircle className="text-osce-danger h-5 w-5 inline" />
                    )}{" "}
                  </td>{" "}
                </tr>
              );
            }
            return null;
          })}{" "}
        </tbody>{" "}
      </table>{" "}
    </div>
  );
};
