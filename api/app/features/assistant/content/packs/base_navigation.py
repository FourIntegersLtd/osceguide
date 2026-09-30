"""Base FAQ: getting started and the navigation sidebar. Labels come from ``{nav.<key>}``."""

from __future__ import annotations

from ..models import FaqEntry

GETTING_STARTED = "Getting started"
NAVIGATION = "Navigation and sidebar labels"

ENTRIES: tuple[FaqEntry, ...] = (
    FaqEntry(
        id="what-is-product",
        section=GETTING_STARTED,
        question="What is OSCE Guide?",
        answer=(
            "OSCE Guide, pronounced osski Guide, is a platform for clinical communication practice. "
            "You run AI practice stations, get structured feedback, and track progress on your dashboard."
        ),
    ),
    FaqEntry(
        id="get-started",
        section=GETTING_STARTED,
        question="How do I get started after I log in?",
        answer=(
            "Open {nav.dashboard} for your overview. To practise cases, click {nav.mocks}, stay on the Setup tab, "
            "set your session name and station count, then click Create Session. Open your session from "
            "View All Sessions when it appears, then start a station when you are ready."
        ),
        requires_nav=("dashboard", "mocks"),
    ),
    FaqEntry(
        id="main-menu",
        section=GETTING_STARTED,
        question="Where is the main menu?",
        answer=(
            "The main menu is the left navigation bar. It shows the pages available to your account, "
            "such as {nav.dashboard}, {nav.mocks}, {nav.messages}, {nav.community}, {nav.settings}, and {nav.achievements}. "
            "Your sidebar only shows what applies to your exam and account."
        ),
    ),
    FaqEntry(
        id="dashboard-vs-practice",
        section=GETTING_STARTED,
        question="What is the difference between Dashboard and AI Practice?",
        answer=(
            "{nav.dashboard} shows performance summaries and charts for your exam. {nav.mocks} is where you create "
            "sessions, run stations, use Combine Stations, and open Flagged Stations."
        ),
        requires_nav=("dashboard", "mocks"),
    ),
    FaqEntry(
        id="lost-first-click",
        section=GETTING_STARTED,
        question="I am lost. What should I click first?",
        answer=(
            "If you want to practise a case, click {nav.mocks}, stay on the Setup tab, fill in your session details, "
            "and click Create Session. If you want to see how you are improving, click {nav.dashboard} first."
        ),
        requires_nav=("dashboard", "mocks"),
    ),
    FaqEntry(
        id="nav-mocks",
        section=NAVIGATION,
        question="Where is AI Practice?",
        answer="Click {nav.mocks} in the left navigation bar. It opens the Practice area where you set up sessions and manage stations.",
        requires_nav=("mocks",),
    ),
    FaqEntry(
        id="nav-practice-alias",
        section=NAVIGATION,
        question="Where is Practise or Practice in the menu?",
        answer="In the app the sidebar item is called {nav.mocks}. Click that to create sessions and run stations.",
        requires_nav=("mocks",),
    ),
    FaqEntry(
        id="nav-contact",
        section=NAVIGATION,
        question="Where is Contact Us?",
        answer="Click {nav.messages} in the left navigation bar. It opens the messages page where you can reach the team.",
        requires_nav=("messages",),
    ),
    FaqEntry(
        id="nav-settings",
        section=NAVIGATION,
        question="Where are Settings?",
        answer="Click {nav.settings} in the left navigation bar to manage your account, subscription, and related options.",
        requires_nav=("settings",),
    ),
    FaqEntry(
        id="nav-community",
        section=NAVIGATION,
        question="Where is Community?",
        answer="Click {nav.community} in the left navigation bar to read posts and interact with other learners.",
        requires_nav=("community",),
    ),
    FaqEntry(
        id="nav-achievements",
        section=NAVIGATION,
        question="Where are Achievements?",
        answer="Click {nav.achievements} in the left navigation bar to view your milestones and badges.",
        requires_nav=("achievements",),
    ),
    FaqEntry(
        id="nav-missing-item",
        section=NAVIGATION,
        question="Why can I not see a menu item that someone else has?",
        answer=(
            "The sidebar only shows the pages that apply to your exam and account type. "
            "If a page you expect is missing, check {nav.settings} for your exam, or ask the team through {nav.messages}."
        ),
    ),
)
