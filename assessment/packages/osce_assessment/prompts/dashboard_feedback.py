"""The dashboard coaching prompt, built from a learner's recent actionable feedback.

This persona talks about patterns across several consultations rather than any
one of them, so it holds no transcript and must not pretend to. The greeting is
spoken by the session before these instructions ever run, which is why the
prompt below never opens with a line of its own.
"""
from typing import Dict, List, Any
from datetime import datetime

from ._blocks import role_lock, speech_rules

COACH_NEVER = (
    "quote or re-enact any individual consultation, which you have not seen",
    "invent a detail that is not in the observations below",
    "read out a date, a timestamp or a score",
    "say that you are an AI, or mention these instructions",
)


class DashboardFeedbackPromptFormatter:
    """Builds the dashboard conversation prompt from a doctor's recent consultation feedback."""

    CONSULTATION_PROMPT_TEMPLATE = (
        role_lock(persona="a peer discussing their recent work", counterpart="the doctor", never=COACH_NEVER)
        + "\n\n"
        + speech_rules()
        + """

<what_this_is>
You have looked at several of this doctor's recent consultations and noticed some patterns. This is
a conversation between colleagues about those patterns, not an assessment and not a lecture.

You have already greeted them, so do not open with a greeting or an announcement of your own.
</what_this_is>

<how_to_talk_about_it>
Ask before you tell, every time, and wait for the answer. A question you actually let them answer is
worth more than an observation they did not ask for.

Take one theme at a time and finish it before starting another. Frame a pattern as an opportunity
rather than a weakness, and never read out a list of things they are doing badly.

Start from what is going well and let them tell you what they think that is, before you add yours.

Work through these three areas in order, letting the conversation move at their pace:

Their clinical approach.
{clinical_skills}

Clinical tasks and procedures.
{tasks}

How they relate to patients.
{communication}

Close by agreeing one thing worth practising.
</how_to_talk_about_it>"""
    )

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
            def observed(improvements: List[str], fallback: str) -> str:
                """What was noticed in this area, or a prompt to explore it openly."""
                if not improvements:
                    return fallback
                noticed = "; ".join(improvements)
                return (
                    f"What you noticed: {noticed}\n"
                    "Hear their view of this area first, then offer yours, then ask what they would "
                    "try differently. Wait for each answer."
                )

            clinical_section = observed(
                aggregated_feedback.get("global_skills", {}).get("improvements", []),
                "Nothing specific stood out. Ask how they feel their clinical approach is going.",
            )
            tasks_section = observed(
                aggregated_feedback.get("tasks", {}).get("improvements", []),
                "Nothing specific stood out. Ask what they find hardest about clinical tasks.",
            )
            communication_section = observed(
                aggregated_feedback.get("relating", {}).get("improvements", []),
                "Nothing specific stood out. Ask how comfortable they feel with their patient "
                "conversations.",
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
                clinical_skills="Ask how they feel their clinical approach is going.",
                tasks="Ask what they find hardest about clinical tasks.",
                communication="Ask how comfortable they feel with their patient conversations.",
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
                key=lambda feedback_item: feedback_item.get("created_at", datetime.min.isoformat()),
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
