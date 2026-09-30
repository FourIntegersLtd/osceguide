"""Base FAQ: dashboard, feedback scores and community. Exam overlays add their own panels."""

from __future__ import annotations

from ..models import FaqEntry

DASHBOARD = "Performance Dashboard"
SCORES = "Understanding your feedback scores"
COMMUNITY = "Community"

ENTRIES: tuple[FaqEntry, ...] = (
    FaqEntry(
        "see-progress",
        DASHBOARD,
        "Where can I see my progress?",
        "Click {nav.dashboard} in the left navigation bar. You can view performance trends and improvement over time there.",
        ("dashboard",),
    ),
    FaqEntry(
        "focus-improving",
        DASHBOARD,
        "What should I focus on improving?",
        "Open {nav.dashboard} and use your charts and latest station feedback to choose what to practise next in {nav.mocks}.",
        ("dashboard", "mocks"),
    ),
    FaqEntry(
        "red-scores",
        SCORES,
        "Should I worry about Red scores?",
        "Where Red appears, it simply marks a skill to prioritise. It is common early on and improves with targeted practice.",
    ),
    FaqEntry(
        "score-x-of-y",
        SCORES,
        "What does a score like 7 of 11 mean?",
        "It usually means seven skills were rated satisfactory out of eleven assessed in that area. Each exam presents scores in its own feedback screens; open the Feedback tab on the station for the breakdown.",
    ),
    FaqEntry(
        "community-how",
        COMMUNITY,
        "How does the community work?",
        "{nav.community} is a space to share thoughts, ask questions, and learn from peers preparing for similar exams. Be respectful and follow guidelines. Offensive content may be removed.",
        ("community",),
    ),
)
