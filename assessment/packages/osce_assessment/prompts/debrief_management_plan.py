"""Renders a station management plan for the debrief tutor and the consulting doctor."""
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
                "title": "Explanation", "audience": "patient", "priority": "core",
                "content": plan.get("explanation", "No explanation provided"),
            },
            {
                "title": "Differential Diagnosis", "audience": "doctor",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("differential_diagnosis")
                ),
                "optional": True,
            },
            {
                "title": "Examination Findings", "audience": "doctor",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("examination_findings")
                ),
                "optional": True,
            },
            {
                "title": "Assessment", "audience": "doctor",
                "content": ManagementPlanFormatter._safe_join(plan.get("assessment"))
                or "No assessment provided",
            },
            {
                "title": "Further Investigations", "audience": "patient", "priority": "core",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("further_investigations")
                ),
                "optional": True,
            },
            {
                "title": "Social Concerns", "audience": "doctor",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("social_concerns")
                ),
                "optional": True,
            },
            {
                "title": "Information, Concerns, Expectations", "audience": "doctor",
                "content": ManagementPlanFormatter._safe_join(plan.get("ice")),
                "optional": True,
            },
            {
                "title": "Immediate Actions", "audience": "patient", "priority": "core",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("immediate_actions")
                ),
                "optional": True,
            },
            {
                "title": "Pharmacological Treatment", "audience": "patient", "priority": "core",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("pharmacological_treatment")
                ),
                "optional": True,
            },
            {
                "title": "Non-Pharmacological Treatment", "audience": "patient", "priority": "if_time",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("non_pharmacological_treatment")
                ),
                "optional": True,
            },
            {
                "title": "Follow-up", "audience": "patient", "priority": "core",
                "content": plan.get("follow_up"),
                "optional": True,
            },
            {
                "title": "Health Education", "audience": "patient", "priority": "if_time",
                "content": ManagementPlanFormatter._safe_join(
                    plan.get("health_education")
                ),
                "optional": True,
            },
            {
                "title": "Safety Netting", "audience": "patient", "priority": "core",
                "content": plan.get("safety_netting"),
                "optional": True,
            },
            {
                "title": "Additional Notes", "audience": "doctor",
                "content": plan.get("additional_notes"),
                "optional": True,
            },
        ]

    @staticmethod
    def section_titles(
        plan: Optional[Dict], *, audience: Optional[str] = None, priority: Optional[str] = None
    ) -> List[str]:
        """The headings this plan will actually render, in the order it renders them.

        The consulting-doctor prompt asks the model to work through the plan
        section by section, so it needs the real list. Restating that order by
        hand drifts: it did, and the section it stopped naming was the one the
        model then stopped covering.

        ``audience`` narrows to the headings written for one party. A plan is
        not a script: ``Assessment`` holds prompts like "check mood" and
        ``Differential Diagnosis`` holds the doctor's own reasoning, so asking
        for those to be said aloud to a patient asks for nonsense. Pass
        ``"patient"`` for the content a consultation must actually deliver, or
        ``"doctor"`` for what the clinician works from.
        """
        if not ManagementPlanFormatter._is_valid_plan(plan):
            return []
        return [
            section["title"]
            for section in ManagementPlanFormatter._plan_section_definitions(plan)
            if (not section.get("optional", False) or section["content"])
            and (audience is None or section.get("audience") == audience)
            and (priority is None or section.get("priority") == priority)
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
    def format(management_plan: Optional[Dict]) -> str:
        """
        Formats the entire management plan into a markdown string.

        Args:
            management_plan: Dictionary containing the management plan sections

        Returns:
            Formatted markdown string of the management plan
        """
        try:
            if not ManagementPlanFormatter._is_valid_plan(management_plan):
                return ManagementPlanFormatter.DEFAULT_PLAN

            return ManagementPlanFormatter._format_plan_sections(management_plan)
        except Exception:
            return ManagementPlanFormatter.DEFAULT_PLAN
