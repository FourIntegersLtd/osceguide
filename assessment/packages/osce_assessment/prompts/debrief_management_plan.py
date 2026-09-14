"""Renders a station management plan (or interview questions) for the debrief tutor."""
from typing import Any, Dict, List, Optional


class ManagementPlanFormatter:
    DEFAULT_PLAN = """
    ## Management Plan
    Basic consultation requirements:
    - Clear communication
    - Patient-centered approach
    - Structured consultation
    - Safety netting
    - Clear follow-up plan"""

    @staticmethod
    def _is_valid_plan(plan: Optional[Dict]) -> bool:
        """
        Validates if the management plan contains any valid data.
        """
        if not plan or not isinstance(plan, dict):
            return False

        return any(
            value
            and (
                (isinstance(value, str) and value.strip())
                or (isinstance(value, list) and len(value) > 0)
            )
            for value in plan.values()
        )

    @staticmethod
    def _safe_join(arr: Optional[List[str]]) -> str:
        """
        Safely joins array elements with newlines.
        """
        return "\n".join(arr) if isinstance(arr, list) else ""

    @staticmethod
    def _plan_section_definitions(plan: Dict) -> List[Dict[str, Any]]:
        """Ordered section metadata + content for a management plan dict."""
        return [
            {
                "title": "Explanation",
                "content": plan.get("explanation", "No explanation provided"),
            },
            {
                "title": "Differential Diagnosis",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("differential_diagnosis")
                ),
                "optional": True,
            },
            {
                "title": "Examination Findings",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("examination_findings")
                ),
                "optional": True,
            },
            {
                "title": "Assessment",
                "content": ManagementPlanFormatter._safe_join(plan.get("assessment"))
                or "No assessment provided",
            },
            {
                "title": "Further Investigations",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("further_investigations")
                ),
                "optional": True,
            },
            {
                "title": "Social Concerns",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("social_concerns")
                ),
                "optional": True,
            },
            {
                "title": "Information, Concerns, Expectations",
                "content": ManagementPlanFormatter._safe_join(plan.get("ice")),
                "optional": True,
            },
            {
                "title": "Immediate Actions",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("immediate_actions")
                ),
                "optional": True,
            },
            {
                "title": "Pharmacological Treatment",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("pharmacological_treatment")
                ),
                "optional": True,
            },
            {
                "title": "Non-Pharmacological Treatment",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("non_pharmacological_treatment")
                ),
                "optional": True,
            },
            {
                "title": "Follow-up",
                "content": plan.get("follow_up"),
                "optional": True,
            },
            {
                "title": "Health Education",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("health_education")
                ),
                "optional": True,
            },
            {
                "title": "Safety Netting",
                "content": plan.get("safety_netting"),
                "optional": True,
            },
            {
                "title": "Additional Notes",
                "content": plan.get("additional_notes"),
                "optional": True,
            },
        ]

    @staticmethod
    def _format_plan_sections(plan: Dict) -> str:
        """
        Formats each section of the management plan.
        """
        formatted_sections = []
        for section in ManagementPlanFormatter._plan_section_definitions(plan):
            if not section.get("optional", False) or section["content"]:
                formatted_sections.append(
                    f"## {section['title']}\n{section['content']}"
                )

        return "\n\n".join(formatted_sections).strip()

    @staticmethod
    def format(
        management_plan: Optional[Dict],
        *,
        interview_questions: bool = False,
        station_obj: Optional[Dict] = None,
        candidate_cv_markdown: Optional[str] = None,
    ) -> str:
        """
        Formats the entire management plan into a markdown string.
        With interview_questions=True, formats the station's interview questions
        instead of a management plan (the orthopaedic interview format).

        Args:
            management_plan: Dictionary containing the management plan sections
            interview_questions: Debrief on interview Q&A rather than a management plan
            station_obj: Station object (required for ortho to extract interview_questions)

        Returns:
            Formatted markdown string of the management plan or interview questions
        """
        try:
            if interview_questions:
                return ManagementPlanFormatter.format_ortho_interview_questions(
                    station_obj,
                    candidate_cv_markdown=candidate_cv_markdown,
                )

            if not ManagementPlanFormatter._is_valid_plan(management_plan):
                return ManagementPlanFormatter.DEFAULT_PLAN

            return ManagementPlanFormatter._format_plan_sections(management_plan)
        except Exception as e:
            return ManagementPlanFormatter.DEFAULT_PLAN

    @staticmethod
    def format_ortho_interview_questions(
        station_obj: Optional[Dict],
        *,
        candidate_cv_markdown: Optional[str] = None,
    ) -> str:
        """
        Formats ortho station interview questions and answers into a markdown string.

        Args:
            station_obj: Dictionary containing the ortho station data with interview_questions

        Returns:
            Formatted markdown string of interview questions and answers
        """
        DEFAULT_ORTHO_PLAN = """
        ## Interview Questions & Answers
        No interview questions available for this station."""

        try:
            if not station_obj or not isinstance(station_obj, dict):
                return DEFAULT_ORTHO_PLAN

            interview_questions = station_obj.get("interview_questions", [])
            cv_section = ""
            if candidate_cv_markdown:
                cv_section = f"## Candidate CV\n{candidate_cv_markdown}\n\n"

            if not interview_questions or not isinstance(interview_questions, list):
                return DEFAULT_ORTHO_PLAN

            # Portfolio debrief: CV sections (when present) are included before Interview Q&A.
            # (Portfolio personalisation instruction is in debrief prompt via DebriefPromptFormatter.)
            sections = (
                [cv_section, "## Interview Questions & Answers\n"]
                if cv_section
                else ["## Interview Questions & Answers\n"]
            )

            for idx, qa in enumerate(interview_questions, 1):
                if isinstance(qa, dict):
                    question = qa.get("question", "")
                    answer = qa.get("answer", "")

                    if question or answer:
                        sections.append(f"### Question {idx}")
                        if question:
                            sections.append(f"**Q:** {question}\n")
                        if answer:
                            sections.append(f"**A:** {answer}\n")
                        sections.append("")  # Add spacing between Q&A pairs

            # Return default only when there is no CV and no Q&A content
            has_qa = any("### Question" in s for s in sections)
            if not cv_section and not has_qa:
                return DEFAULT_ORTHO_PLAN

            return "\n".join(sections).strip()

        except Exception as e:
            return DEFAULT_ORTHO_PLAN
