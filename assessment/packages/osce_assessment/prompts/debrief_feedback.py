"""Renders a stored feedback document for the debrief tutor, per exam shape.

Ported verbatim from the legacy worker; snapshot tests prove byte parity.
"""
from typing import Dict, Optional

class ScaFeedbackFormatter:
    DEFAULT_FEEDBACK = """
    ## Consultation Feedback
    No feedback available. This might be because:
    - The consultation is still being evaluated
    - There were technical issues
    - The feedback is being processed

    Please check back later for detailed feedback."""

    @staticmethod
    def format(feedback: Optional[Dict]) -> str:
        """
        Formats a feedback object into a markdown string.
        
        Args:
            feedback: Dictionary containing feedback data matching ScaFeedbackResponseModel
        
        Returns:
            Formatted markdown string of the feedback
        """
        try:
            if not ScaFeedbackFormatter._is_valid_feedback(feedback):
                return ScaFeedbackFormatter.DEFAULT_FEEDBACK

            sections = []
            
            # Format Global Skills section
            if "global_skills" in feedback:
                sections.append(ScaFeedbackFormatter._format_global_skills(feedback["global_skills"]))
            
            # Format Tasks section
            if "tasks" in feedback:
                sections.append(ScaFeedbackFormatter._format_tasks(feedback["tasks"]))
            
            # Format Relating to Others section
            if "relating_to_others" in feedback:
                sections.append(ScaFeedbackFormatter._format_relating(feedback["relating_to_others"]))
            
            # Format Actionable Feedback section
            if "actionable_feedback" in feedback:
                sections.append(ScaFeedbackFormatter._format_actionable(feedback["actionable_feedback"]))

            return "\n\n".join(sections) if sections else ScaFeedbackFormatter.DEFAULT_FEEDBACK

        except Exception as e:
            return ScaFeedbackFormatter.DEFAULT_FEEDBACK

    @staticmethod
    def _is_valid_feedback(feedback: Optional[Dict]) -> bool:
        """
        Validates the feedback object structure.
        
        Args:
            feedback: Dictionary containing feedback data
            
        Returns:
            Boolean indicating if feedback is valid
        """
        return bool(
            feedback
            and isinstance(feedback, dict)
            and any(key in feedback for key in ["global_skills", "tasks", "relating_to_others"])
        )

    @staticmethod
    def _format_score_section(title: str, score_data: Dict) -> str:
        """
        Formats a score section with supporting evidence.
        
        Args:
            title: Section title
            score_data: Dictionary containing score, supporting_phrase, and score_explanation
            
        Returns:
            Formatted markdown string
        """
        return f"""### {title}
Score: {score_data.get('score', 'N/A')}
Supporting Evidence: {score_data.get('supporting_phrase', '')}
Explanation: {score_data.get('score_explanation', '')}"""

    @staticmethod
    def _format_global_skills(global_skills: Dict) -> str:
        """
        Formats the global skills section.
        """
        sections = ["## Global Skills"]
        for skill, data in global_skills.items():
            if isinstance(data, dict):
                title = skill.replace('_', ' ').title()
                sections.append(ScaFeedbackFormatter._format_score_section(title, data))
        return "\n\n".join(sections)

    @staticmethod
    def _format_tasks(tasks: Dict) -> str:
        """
        Formats the tasks section.
        """
        sections = ["## Clinical Tasks"]
        for task, data in tasks.items():
            if isinstance(data, dict):
                title = task.replace('_', ' ').title()
                sections.append(ScaFeedbackFormatter._format_score_section(title, data))
        return "\n\n".join(sections)

    @staticmethod
    def _format_relating(relating: Dict) -> str:
        """
        Formats the relating to others section.
        """
        sections = ["## Relating to Others"]
        for skill, data in relating.items():
            if isinstance(data, dict):
                title = skill.replace('_', ' ').title()
                sections.append(ScaFeedbackFormatter._format_score_section(title, data))
        return "\n\n".join(sections)

    @staticmethod
    def _format_actionable(actionable: Dict) -> str:
        """
        Formats the actionable feedback section.
        """
        sections = ["## Actionable Feedback"]
        
        # Format domain feedback
        for domain in ["global_skills_feedback", "tasks_feedback", "relating_feedback"]:
            if domain in actionable:
                domain_data = actionable[domain]
                title = domain.replace('_', ' ').title()
                sections.append(f"### {title}")
                sections.append(f"Overall Score: {domain_data.get('score', 'N/A')}")
                
                if domain_data.get('strengths'):
                    sections.append("Strengths:")
                    sections.extend([f"- {strength}" for strength in domain_data['strengths']])
                
                if domain_data.get('improvements'):
                    sections.append("\nAreas for Improvement:")
                    sections.extend([f"- {improvement}" for improvement in domain_data['improvements']])

        # Format priority actions
        if actionable.get('overall_priorities'):
            sections.append("\n### Priority Actions")
            for priority in actionable['overall_priorities']:
                sections.append(f"""
Area: {priority.get('area')}
Current Level: {priority.get('current_level')}
Improvement Steps:""")
                sections.extend([f"- {step}" for step in priority.get('improvement_steps', [])])
                sections.append(f"Expected Outcome: {priority.get('expected_outcome')}\n")

        return "\n\n".join(sections)


class PlabFeedbackFormatter:
    DEFAULT_FEEDBACK = """
    ## PLAB Station Feedback
    No feedback available. This might be because:
    - The station is still being evaluated
    - There were technical issues
    - The feedback is being processed

    Please check back later for detailed feedback."""

    @staticmethod
    def format(feedback: Optional[Dict]) -> str:
        """
        Formats a PLAB feedback object into a markdown string.
        
        Args:
            feedback: Dictionary containing feedback data matching PlabStationFeedbackModel
        
        Returns:
            Formatted markdown string of the feedback
        """
        try:
            if not PlabFeedbackFormatter._is_valid_feedback(feedback):
                return PlabFeedbackFormatter.DEFAULT_FEEDBACK

            sections = []
            
            # Format each domain
            domains = [
                ("data_gathering", "Data Gathering"),
                ("clinical_management", "Clinical Management"),
                ("interpersonal_skills", "Interpersonal Skills")
            ]
            
            for domain_key, domain_title in domains:
                if domain_key in feedback:
                    sections.append(PlabFeedbackFormatter._format_domain(
                        domain_title, 
                        feedback[domain_key]
                    ))

            return "\n\n".join(sections) if sections else PlabFeedbackFormatter.DEFAULT_FEEDBACK

        except Exception as e:
            return PlabFeedbackFormatter.DEFAULT_FEEDBACK

    @staticmethod
    def _is_valid_feedback(feedback: Optional[Dict]) -> bool:
        """Validates the feedback object structure."""
        return bool(
            feedback
            and isinstance(feedback, dict)
            and any(key in feedback for key in [
                "data_gathering",
                "clinical_management",
                "interpersonal_skills"
            ])
        )
        

    @staticmethod
    def _format_competency(title: str, data: Dict) -> str:
        """Formats individual competency data."""
        sections = [f"### {title}"]
        
        # Add score
        score = data.get("score", 0.0)
        sections.append(f"Score: {score:.2f}")
        
        # Add completed tasks
        if data.get("completed"):
            sections.append("\nCompleted Tasks:")
            sections.extend([f"✓ {task}" for task in data["completed"]])
        
        # Add supporting phrases with quotes
        if data.get("supporting_phrase"):
            sections.append("\nEvidence:")
            sections.extend([f'"{phrase}"' for phrase in data["supporting_phrase"]])
        
        # Add missed tasks
        if data.get("missed"):
            sections.append("\nMissed Tasks:")
            sections.extend([f"× {task}" for task in data["missed"]])
        
        # Add critical flags (if any)
        if data.get("critical_flags"):
            sections.append("\n⚠️ Critical Concerns:")
            sections.extend([f"! {flag}" for flag in data["critical_flags"]])
        
        # Add improvement suggestions
        if data.get("suggested_actions"):
            sections.append("\nSuggested Actions:")
            sections.extend([f"- {action}" for action in data["suggested_actions"]])
        
        return "\n".join(sections)

    @staticmethod
    def _format_domain(domain_title: str, domain_data: Dict) -> str:
        """Formats a complete domain section with all its competencies."""
        sections = [f"## {domain_title}"]
        total_score = sum(
            comp.get("score", 0.0) 
            for comp in domain_data.values() 
            if isinstance(comp, dict)
        )
        sections.append(f"Domain Score: {total_score:.1f}/4.0\n")
        
        # Map of domain competencies
        competency_map = {
            "data_gathering": [
                ("history_taking", "History Taking"),
                ("examination", "Examination"),
                ("investigations", "Investigations"),
                ("interpretation", "Clinical Interpretation")
            ],
            "clinical_management": [
                ("diagnosis", "Diagnosis"),
                ("management_plan", "Management Plan"),
                ("safety_netting", "Safety Netting"),
                ("follow_up", "Follow-up Plan")
            ],
            "interpersonal_skills": [
                ("language", "Language & Communication"),
                ("listening", "Active Listening"),
                ("rapport", "Building Rapport"),
                ("empathy", "Empathy & Compassion")
            ]
        }
        
        # Get the correct competency map based on domain title
        domain_key = domain_title.lower().replace(" ", "_")
        competencies = competency_map.get(domain_key, [])
        
        # Format each competency in the domain
        for comp_key, comp_title in competencies:
            if comp_key in domain_data:
                sections.append(PlabFeedbackFormatter._format_competency(
                    comp_title,
                    domain_data[comp_key]
                ))
        
        return "\n\n".join(sections)


class OrthoFeedbackFormatter:
    DEFAULT_FEEDBACK = """
    ## Orthopaedic Station Feedback
    No feedback available. This might be because:
    - The station is still being evaluated
    - There were technical issues
    - The feedback is being processed

    Please check back later for detailed feedback."""

    @staticmethod
    def format(feedback: Optional[Dict], station_type: str = "clinical") -> str:
        """
        Formats an ortho feedback object into a markdown string based on station type.
        
        Args:
            feedback: Dictionary containing feedback data matching OrthoStationFeedbackModel
            station_type: Type of station - "clinical", "prioritisation", or "communication"
        
        Returns:
            Formatted markdown string of the feedback
        """
        try:
            if not OrthoFeedbackFormatter._is_valid_feedback(feedback):
                return OrthoFeedbackFormatter.DEFAULT_FEEDBACK

            station_type = station_type.lower()
            
            if station_type == "clinical":
                return OrthoClinicalSkillFeedbackFormatter.format(feedback)
            elif station_type == "prioritisation":
                return OrthoPrioritisationSkillFeedbackFormatter.format(feedback)
            elif station_type == "communication":
                return OrthoCommunicationSkillFeedbackFormatter.format(feedback)
            elif station_type == "portfolio":
                return OrthoPortfolioSkillFeedbackFormatter.format(feedback)
            else:
                # Fallback to clinical if station_type is unknown
                return OrthoClinicalSkillFeedbackFormatter.format(feedback)

        except Exception as e:
            return OrthoFeedbackFormatter.DEFAULT_FEEDBACK

    @staticmethod
    def _is_valid_feedback(feedback: Optional[Dict]) -> bool:
        """Validates the feedback object structure."""
        return bool(
            feedback
            and isinstance(feedback, dict)
            and any(key in feedback for key in [
                "clinical_skills",
                "prioritisation_skills",
                "communication_skills",
                "portfolio_skills",
            ])
        )


class OrthoClinicalSkillFeedbackFormatter:
    DEFAULT_FEEDBACK = """
    ## Clinical Station Feedback
    No feedback available for this clinical station."""

    @staticmethod
    def format(feedback: Optional[Dict]) -> str:
        """Formats clinical station feedback."""
        try:
            if not feedback or "clinical_skills" not in feedback:
                return OrthoClinicalSkillFeedbackFormatter.DEFAULT_FEEDBACK

            clinical_skills = feedback["clinical_skills"]
            sections = ["## Clinical Station Feedback"]
            
            # Add aggregate score if available
            if isinstance(clinical_skills, dict):
                total_score = sum(
                    skill.get("score", 0)
                    for skill in clinical_skills.values()
                    if isinstance(skill, dict) and "score" in skill
                )
                sections.append(f"**Total Score: {total_score}/50**\n")

            # Format each skill
            skill_map = [
                ("technical_knowledge_clinical_expertise", "Technical Knowledge & Clinical Expertise"),
                ("situational_awareness", "Situational Awareness"),
                ("communication_information_gathering", "Communication & Information Gathering"),
                ("problem_solving_decision_making", "Problem Solving & Decision Making"),
                ("communication_information_giving", "Communication & Information Giving"),
            ]

            for skill_key, skill_title in skill_map:
                if skill_key in clinical_skills:
                    sections.append(
                        OrthoClinicalSkillFeedbackFormatter._format_skill(
                            skill_title, clinical_skills[skill_key]
                        )
                    )

            return "\n\n".join(sections) if sections else OrthoClinicalSkillFeedbackFormatter.DEFAULT_FEEDBACK

        except Exception as e:
            return OrthoClinicalSkillFeedbackFormatter.DEFAULT_FEEDBACK

    @staticmethod
    def _format_skill(title: str, skill_data: Dict) -> str:
        """Formats an individual skill evaluation."""
        sections = [f"### {title}"]
        
        score = skill_data.get("score", 0)
        sections.append(f"**Score: {score}/10**\n")
        
        # Score justification
        if skill_data.get("score_justification"):
            sections.append(f"**Justification:**\n{skill_data['score_justification']}\n")
        
        # Evidence points
        if skill_data.get("evidence_points"):
            sections.append("**Evidence:**")
            sections.extend([f"- {point}" for point in skill_data["evidence_points"]])
            sections.append("")
        
        # Completed tasks
        if skill_data.get("completed"):
            sections.append("**Completed Tasks:**")
            sections.extend([f"✓ {task}" for task in skill_data["completed"]])
            sections.append("")
        
        # Suggested actions
        if skill_data.get("suggested_actions"):
            sections.append("**Suggested Actions:**")
            sections.extend([f"- {action}" for action in skill_data["suggested_actions"]])

        return "\n".join(sections)


class OrthoPrioritisationSkillFeedbackFormatter:
    DEFAULT_FEEDBACK = """
    ## Prioritisation Station Feedback
    No feedback available for this prioritisation station."""

    @staticmethod
    def format(feedback: Optional[Dict]) -> str:
        """Formats prioritisation station feedback."""
        try:
            if not feedback or "prioritisation_skills" not in feedback:
                return OrthoPrioritisationSkillFeedbackFormatter.DEFAULT_FEEDBACK

            prioritisation_skills = feedback["prioritisation_skills"]
            sections = ["## Prioritisation Station Feedback"]
            
            # Add aggregate score if available
            if isinstance(prioritisation_skills, dict):
                total_score = sum(
                    skill.get("score", 0)
                    for skill in prioritisation_skills.values()
                    if isinstance(skill, dict) and "score" in skill
                )
                sections.append(f"**Total Score: {total_score}/50**\n")

            # Format each skill
            skill_map = [
                ("organisation_planning", "Organisation & Planning"),
                ("judgement_under_pressure", "Judgement Under Pressure"),
                ("situational_awareness", "Situational Awareness"),
                ("problem_solving_decision_making", "Problem Solving & Decision Making"),
                ("communication_information_gathering", "Communication & Information Gathering"),
            ]

            for skill_key, skill_title in skill_map:
                if skill_key in prioritisation_skills:
                    sections.append(
                        OrthoPrioritisationSkillFeedbackFormatter._format_skill(
                            skill_title, prioritisation_skills[skill_key]
                        )
                    )

            return "\n\n".join(sections) if sections else OrthoPrioritisationSkillFeedbackFormatter.DEFAULT_FEEDBACK

        except Exception as e:
            return OrthoPrioritisationSkillFeedbackFormatter.DEFAULT_FEEDBACK

    @staticmethod
    def _format_skill(title: str, skill_data: Dict) -> str:
        """Formats an individual skill evaluation."""
        sections = [f"### {title}"]
        
        score = skill_data.get("score", 0)
        sections.append(f"**Score: {score}/10**\n")
        
        # Score justification
        if skill_data.get("score_justification"):
            sections.append(f"**Justification:**\n{skill_data['score_justification']}\n")
        
        # Evidence points
        if skill_data.get("evidence_points"):
            sections.append("**Evidence:**")
            sections.extend([f"- {point}" for point in skill_data["evidence_points"]])
            sections.append("")
        
        # Completed tasks
        if skill_data.get("completed"):
            sections.append("**Completed Tasks:**")
            sections.extend([f"✓ {task}" for task in skill_data["completed"]])
            sections.append("")
        
        # Suggested actions
        if skill_data.get("suggested_actions"):
            sections.append("**Suggested Actions:**")
            sections.extend([f"- {action}" for action in skill_data["suggested_actions"]])

        return "\n".join(sections)


class OrthoCommunicationSkillFeedbackFormatter:
    DEFAULT_FEEDBACK = """
    ## Communication Station Feedback
    No feedback available for this communication station."""

    @staticmethod
    def format(feedback: Optional[Dict]) -> str:
        """Formats communication station feedback."""
        try:
            if not feedback or "communication_skills" not in feedback:
                return OrthoCommunicationSkillFeedbackFormatter.DEFAULT_FEEDBACK

            communication_skills = feedback["communication_skills"]
            sections = ["## Communication Station Feedback"]
            
            # Add aggregate score if available
            if isinstance(communication_skills, dict):
                total_score = sum(
                    skill.get("score", 0)
                    for skill in communication_skills.values()
                    if isinstance(skill, dict) and "score" in skill
                )
                sections.append(f"**Total Score: {total_score}/50**\n")

            # Format each skill
            skill_map = [
                ("communication_information_gathering", "Communication & Information Gathering"),
                ("communication_information_giving", "Communication & Information Giving"),
                ("situational_awareness", "Situational Awareness"),
                ("judgement_under_pressure", "Judgement Under Pressure"),
                ("technical_knowledge_clinical_expertise", "Technical Knowledge & Clinical Expertise"),
            ]

            for skill_key, skill_title in skill_map:
                if skill_key in communication_skills:
                    sections.append(
                        OrthoCommunicationSkillFeedbackFormatter._format_skill(
                            skill_title, communication_skills[skill_key]
                        )
                    )

            return "\n\n".join(sections) if sections else OrthoCommunicationSkillFeedbackFormatter.DEFAULT_FEEDBACK

        except Exception as e:
            return OrthoCommunicationSkillFeedbackFormatter.DEFAULT_FEEDBACK

    @staticmethod
    def _format_skill(title: str, skill_data: Dict) -> str:
        """Formats an individual skill evaluation."""
        sections = [f"### {title}"]
        
        score = skill_data.get("score", 0)
        sections.append(f"**Score: {score}/10**\n")
        
        # Score justification
        if skill_data.get("score_justification"):
            sections.append(f"**Justification:**\n{skill_data['score_justification']}\n")
        
        # Evidence points
        if skill_data.get("evidence_points"):
            sections.append("**Evidence:**")
            sections.extend([f"- {point}" for point in skill_data["evidence_points"]])
            sections.append("")
        
        # Completed tasks
        if skill_data.get("completed"):
            sections.append("**Completed Tasks:**")
            sections.extend([f"✓ {task}" for task in skill_data["completed"]])
            sections.append("")
        
        # Suggested actions
        if skill_data.get("suggested_actions"):
            sections.append("**Suggested Actions:**")
            sections.extend([f"- {action}" for action in skill_data["suggested_actions"]])

        return "\n".join(sections)


class OrthoPortfolioSkillFeedbackFormatter:
    DEFAULT_FEEDBACK = """
    ## Portfolio Station Feedback
    No feedback available for this portfolio station."""

    @staticmethod
    def format(feedback: Optional[Dict]) -> str:
        """Formats portfolio station feedback."""
        try:
            if not feedback or "portfolio_skills" not in feedback:
                return OrthoPortfolioSkillFeedbackFormatter.DEFAULT_FEEDBACK

            portfolio_skills = feedback["portfolio_skills"]
            sections = ["## Portfolio Station Feedback"]

            # Add aggregate score if available
            if isinstance(portfolio_skills, dict):
                total_score = sum(
                    skill.get("score", 0)
                    for skill in portfolio_skills.values()
                    if isinstance(skill, dict) and "score" in skill
                )
                sections.append(f"**Total Score: {total_score}/50**\n")

            # Format each skill
            skill_map = [
                ("person_specifications_cv_articulation", "Person Specifications & CV Articulation"),
                ("portfolio_knowledge", "Portfolio Knowledge"),
                ("reflection_professional_conduct", "Reflection & Professional Conduct"),
                ("communication_information_giving", "Communication & Information Giving"),
                ("critical_thinking_justification", "Critical Thinking & Justification"),
            ]

            for skill_key, skill_title in skill_map:
                if skill_key in portfolio_skills:
                    sections.append(
                        OrthoPortfolioSkillFeedbackFormatter._format_skill(
                            skill_title, portfolio_skills[skill_key]
                        )
                    )

            return "\n\n".join(sections) if sections else OrthoPortfolioSkillFeedbackFormatter.DEFAULT_FEEDBACK

        except Exception as e:
            return OrthoPortfolioSkillFeedbackFormatter.DEFAULT_FEEDBACK

    @staticmethod
    def _format_skill(title: str, skill_data: Dict) -> str:
        """Formats an individual skill evaluation."""
        sections = [f"### {title}"]

        score = skill_data.get("score", 0)
        sections.append(f"**Score: {score}/10**\n")

        # Score justification
        if skill_data.get("score_justification"):
            sections.append(f"**Justification:**\n{skill_data['score_justification']}\n")

        # Evidence points
        if skill_data.get("evidence_points"):
            sections.append("**Evidence:**")
            sections.extend([f"- {point}" for point in skill_data["evidence_points"]])
            sections.append("")

        # Completed tasks
        if skill_data.get("completed"):
            sections.append("**Completed Tasks:**")
            sections.extend([f"✓ {task}" for task in skill_data["completed"]])
            sections.append("")

        # Suggested actions
        if skill_data.get("suggested_actions"):
            sections.append("**Suggested Actions:**")
            sections.extend([f"- {action}" for action in skill_data["suggested_actions"]])

        return "\n".join(sections)