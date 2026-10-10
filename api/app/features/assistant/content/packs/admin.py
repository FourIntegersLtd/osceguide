"""Admin surface overlay: station authoring, the Admin area and Exam tutor."""

from __future__ import annotations

from ..models import FaqEntry
from ..overlay import Overlay
from .base_navigation import NAVIGATION

ADMIN = "Admin tools"

OVERLAY = Overlay(
    greetings={
        "help": "Hi, this is Help. I can help you with the admin tools as well as the learner pages. What do you need?",
    },
    add=(
        FaqEntry(
            "nav-admin",
            NAVIGATION,
            "Where is the Admin area?",
            "Click {nav.admin} in the left navigation. It only appears for admin accounts.",
            ("admin",),
        ),
        FaqEntry(
            "nav-exam-tutor",
            NAVIGATION,
            "Where is Exam tutor?",
            "Click {nav.examinations} in the left navigation. It only appears for admin accounts.",
            ("examinations",),
        ),
        FaqEntry(
            "admin-edit-station",
            ADMIN,
            "How do I edit a station?",
            "Open {nav.admin}, find the station in the list, and open its update form. Save when you are done; changes apply to new attempts.",
            ("admin",),
        ),
        FaqEntry(
            "admin-test-station",
            ADMIN,
            "How do I test a station as the patient before publishing?",
            "Open the station's update form under {nav.admin} and use the test consultation control at the bottom of the form. It runs the AI patient against the current station data without recording an attempt.",
            ("admin",),
        ),
        FaqEntry(
            "admin-station-images",
            ADMIN,
            "How do I add or replace images on a station?",
            "Open the station's update form under {nav.admin}, use the image upload control, then save the form. Refresh the station page to confirm the new image shows.",
            ("admin",),
        ),
        FaqEntry(
            "admin-exam-tutor",
            ADMIN,
            "What is Exam tutor?",
            "{nav.examinations} is an admin-only voice tutor for examination technique. Pick an examination from the list and start the session.",
            ("examinations",),
        ),
        FaqEntry(
            "admin-user-support",
            ADMIN,
            "How do I help a user who reports a lost attempt?",
            "Ask for the session and station names, check the attempt in {nav.admin}, and reset the attempt from the station's admin controls if a technical failure burned it.",
            ("admin",),
        ),
    ),
)
