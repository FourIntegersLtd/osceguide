"""
Formats structured CV data (OrthoCV-shaped dict) into a string suitable for LLM context.
Used e.g. in portfolio station debriefs so the LLM has candidate background.
"""
from typing import Dict, Optional

# Field order and titles matching OrthoCVModel (backend/ortho/models/cv/OrthoCVModel.py)
CV_SECTIONS = [
    ("summary", "Summary"),
    ("experience", "Experience"),
    ("education", "Education"),
    ("research", "Research"),
    ("publications", "Publications"),
    ("audits", "Audits"),
    ("teaching", "Teaching"),
    ("leadership", "Leadership"),
    ("achievements", "Achievements"),
    ("skills", "Skills"),
    ("grants", "Grants"),
    ("courses", "Courses"),
]


def format_structured_cv_for_llm(structured_cv: Optional[Dict]) -> str:
    """
    Format structured CV data (from OrthoCV / structured_cv in Firestore) into
    a markdown string for LLM context (e.g. debrief instructions).

    Args:
        structured_cv: Dict with keys matching OrthoCVModel (summary, experience,
            education, research, publications, audits, teaching, leadership,
            achievements, skills, grants, courses). Values are optional strings.

    Returns:
        Markdown string with ## Section headers and content for non-empty fields.
        Empty string if structured_cv is None/empty or has no content.
    """
    if not structured_cv or not isinstance(structured_cv, dict):
        return ""

    sections = []
    for key, title in CV_SECTIONS:
        value = structured_cv.get(key)
        if value and isinstance(value, str) and value.strip():
            sections.append(f"## {title}\n{value.strip()}")

    if not sections:
        return ""

    return "\n\n".join(sections).strip()
