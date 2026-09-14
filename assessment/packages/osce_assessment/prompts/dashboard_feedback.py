"""The dashboard coaching prompt, built from a learner's recent actionable feedback."""
from typing import Dict, List, Any
from datetime import datetime


class DashboardFeedbackPromptFormatter:
    CONSULTATION_PROMPT_TEMPLATE = """
    You are having a supportive peer-to-peer conversation with a fellow experienced doctor, discussing patterns observed across their recent consultations. Keep the tone informal, collaborative, and constructive.

    CRITICAL TTS WRITING INSTRUCTIONS:
    Write all your responses in plain text format that a Text-to-Speech model can read naturally.
    Do NOT use symbols like #, *, -, _, [], {{}} in your responses.
    Use only plain text, periods, commas, and question marks.
    Write as if you're having a natural conversation without any formatting symbols.

    # Conversation Approach
    - Start with "We've had a chance to observe several of your recent consultations..."
    - Focus on patterns rather than specific timestamps
    - Frame feedback as opportunities for enhancement
    - Use collaborative language like "we" and "let's explore"
    - Make suggestions through questions and gentle prompts
    - WAIT FOR THE DOCTOR'S RESPONSE after each question or topic

    # Discussion Flow (Follow this sequence strictly)
    1. Opening (Build Rapport)
       - Start with: "I noticed some really good things in your consultations..."
       - Ask: "What aspects of your consultations do you feel are going well?"
       - WAIT for their reflection before proceeding

    2. Explore First Area: Clinical Skills
    {clinical_skills}
       - Ask: "How do you feel about your clinical approach?"
       - Listen and discuss their perspective
       - Only then share your observations
       - Suggest one improvement at a time
       - WAIT for engagement before moving on

    3. Discuss Second Area: Tasks & Procedures
    {tasks}
       - Ask: "What challenges do you face with clinical tasks?"
       - Allow them to identify areas for improvement
       - Share your observations supportively
       - Explore solutions together
       - WAIT for their input before continuing

    4. Address Final Area: Communication
    {communication}
       - Ask: "How comfortable do you feel about your patient interactions?"
       - Let them lead the discussion
       - Add your insights gently
       - Discuss specific strategies
       - WAIT for their thoughts before concluding

    # Key Reminders
    - Never read out timestamps
    - Don't list weaknesses - discuss patterns
    - Focus on one theme at a time
    - Use natural conversation flow
    - Include pauses for reflection
    - Maintain peer-to-peer supportive tone
    - ALWAYS wait for the doctor's response before moving to the next topic

    Remember: This is a supportive conversation between colleagues, not a formal assessment. Focus on growth and learning together."""

    DEFAULT_FEEDBACK = "No specific feedback available. Let's discuss general consultation skills and strategies."

    @staticmethod
    def format_actionable_feedback_for_llm(aggregated_feedback: Dict[str, Any]) -> str:
        """
        Format aggregated feedback into a prompt for LLM processing.

        Args:
            aggregated_feedback: Dictionary containing feedback categories and improvements
                Format: {
                    "global_skills": {"improvements": [...]},
                    "tasks": {"improvements": [...]},
                    "relating": {"improvements": [...]}
                }

        Returns:
            Formatted prompt string
        """
        try:
            # Format each section with interactive prompts
            clinical_skills = aggregated_feedback.get("global_skills", {}).get(
                "improvements", []
            )
            clinical_section = (
                """
            If they mention clinical skills:
            • Acknowledge their perspective
            • Then gently explore: "{}"
            • Ask how they might approach this differently
            • WAIT for their response""".format(
                    '" or "'.join(clinical_skills)
                )
                if clinical_skills
                else "   • Explore general clinical approach"
            )

            tasks = aggregated_feedback.get("tasks", {}).get("improvements", [])
            tasks_section = (
                """
            If they bring up clinical tasks:
            • Listen to their experiences
            • Then discuss: "{}"
            • Ask what support they need
            • WAIT for their response""".format(
                    '" or "'.join(tasks)
                )
                if tasks
                else "   • Discuss general task management"
            )

            communication = aggregated_feedback.get("relating", {}).get(
                "improvements", []
            )
            communication_section = (
                """
            If communication comes up:
            • Hear their perspective
            • Then explore: "{}"
            • Ask what strategies they might try
            • WAIT for their response""".format(
                    '" or "'.join(communication)
                )
                if communication
                else "   • Explore general communication style"
            )

            formatted_prompt = (
                DashboardFeedbackPromptFormatter.CONSULTATION_PROMPT_TEMPLATE.format(
                    clinical_skills=clinical_section,
                    tasks=tasks_section,
                    communication=communication_section,
                )
            )

            return formatted_prompt

        except Exception as e:
            return DashboardFeedbackPromptFormatter.CONSULTATION_PROMPT_TEMPLATE.format(
                clinical_skills="   • Explore general clinical approach",
                tasks="   • Discuss general task management",
                communication="   • Explore general communication style",
            )

    @staticmethod
    def _format_bullet_points(items: List[str]) -> str:
        """Format a list of items as bullet points."""
        if not items:
            return "No specific feedback available for this area"
        return "\n".join(f"• {item}" for item in items)

    @staticmethod
    def aggregate_actionable_feedback(
        feedback_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Aggregate and deduplicate feedback from multiple sessions.

        Args:
            feedback_list: List of feedback dictionaries containing actionable_feedback

        Returns:
            Dictionary containing aggregated feedback by category
        """
        try:

            # Initialize aggregated feedback structure
            aggregated_feedback = {
                "global_skills": {"improvements": []},
                "tasks": {"improvements": []},
                "relating": {"improvements": []},
            }

            if not feedback_list:
                return aggregated_feedback

            # Sort feedback by creation date and take most recent 6 feedbacks
            sorted_feedback = sorted(
                feedback_list,
                key=lambda x: x.get("created_at", datetime.min.isoformat()),
                reverse=True,
            )[:12]

            for feedback in sorted_feedback:
                try:
                    actionable_feedback = feedback.get("actionable_feedback", {})

                    # Extract improvements for each category
                    for category in ["global_skills", "tasks", "relating"]:
                        improvements = actionable_feedback.get(
                            f"{category}_feedback", {}
                        ).get("improvements", [])
                        aggregated_feedback[category]["improvements"].extend(
                            improvements
                        )

                except Exception as e:

                    continue

            # Remove duplicates while preserving order
            for domain in aggregated_feedback:
                improvements = aggregated_feedback[domain]["improvements"]
                aggregated_feedback[domain]["improvements"] = list(
                    dict.fromkeys(improvements)
                )

            return aggregated_feedback

        except Exception as e:
            return {
                "global_skills": {"improvements": []},
                "tasks": {"improvements": []},
                "relating": {"improvements": []},
            }
