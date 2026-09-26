"""Base FAQ: creating sessions, combining and flagging stations, and station actions."""

from __future__ import annotations

from ..models import FaqEntry

SETUP = "AI Practice — Setup and sessions"
COMBINE = "Combine sessions and flagged stations"
ACTIONS = "Session list and station actions"

_MOCKS_NAV = ("mocks",)

ENTRIES: tuple[FaqEntry, ...] = (
    FaqEntry(
        "start-session",
        SETUP,
        "How do I start a new session?",
        "Click {nav.mocks} in the left navigation. Make sure you are on the Setup tab. Enter a session name, choose how many stations you want, then click Create Session at the bottom.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "create-session",
        SETUP,
        "How do I create a practice session?",
        "Go to {nav.mocks}, Setup tab, choose the number of stations and confirm your session name, then click Create Session.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "previous-sessions",
        SETUP,
        "Where can I find my previous sessions?",
        "Go to {nav.mocks}, Setup tab. At the bottom click View All Sessions to open your full list of mocks and sessions.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "all-mocks",
        SETUP,
        "How do I see all my mocks?",
        "Click {nav.mocks}, then on the Setup tab click View All Sessions. That page lists your sessions.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "practice-tabs",
        SETUP,
        "What are the tabs on the AI Practice page?",
        "Setup is where you create sessions and open View All Sessions. Combine Stations builds a session from stations you already attempted. Flagged Stations lists cases you marked with a flag.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "setup-tab",
        SETUP,
        "What is the Setup tab?",
        "Setup is the first tab under {nav.mocks}. You use it to name your session, pick how many stations to include, and click Create Session. You can also open View All Sessions from there.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "free-trial",
        SETUP,
        "How do I start a free trial?",
        "After you sign up and log in, go to {nav.mocks}, Setup tab, choose how many stations you want, and click Create Session. Trial access is limited compared with a paid plan. If Create Session asks you to upgrade, or you cannot see any stations, follow the upgrade prompt or open {nav.messages}.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "twelve-stations",
        SETUP,
        "Can I run twelve stations back to back?",
        "Yes. On {nav.mocks}, Setup tab, set the station count to twelve, then click Create Session. Open that session from View All Sessions and work through the stations in order.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "choose-topic",
        SETUP,
        "Can I choose a specific topic or specialty for AI cases?",
        "You currently cannot pick one specialty or named topic up front. Stations are assigned randomly when the session is created. To revisit cases you already did, use Combine Stations or open them from View All Sessions.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "include-previous",
        SETUP,
        "What does Include previously attempted stations mean?",
        "When this option appears on the setup form, turning it on lets the session pull in stations from an earlier subscription period. Leaving it off limits you to stations from your current access. Turn it on after you resubscribe if you want to review or retry stations from a previous plan.",
    ),
    FaqEntry(
        "resubscribed-old-stations",
        SETUP,
        "I resubscribed. How do I get my old stations back?",
        "Go to {nav.mocks}, Setup tab, turn on Include previously attempted stations if shown, then create a new session, or use Combine Stations to rebuild from stations you already attempted. If old attempts are still locked, use {nav.messages} and name the sessions.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "session-locked",
        SETUP,
        "Why is my session locked?",
        "Sessions can show as locked when they belong to an older subscription that is no longer active. Start a new session under your current subscription from the Setup tab, or upgrade in {nav.settings} if you need access.",
    ),
    FaqEntry(
        "delete-session",
        SETUP,
        "How do I delete a session?",
        "Open View All Sessions from {nav.mocks} Setup. Use the delete or trash control on the session you want to remove, and confirm if asked.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "combine-stations",
        COMBINE,
        "How do I combine stations?",
        "Click {nav.mocks}, then open the Combine Stations tab. Enter a name for the new session, select stations you have already attempted, then click Create Session.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "merge-stations",
        COMBINE,
        "How do I merge stations into one mock?",
        "Use {nav.mocks}, Combine Stations tab. Pick the stations you want from your previous attempts and create a named session.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "goto-flagged",
        COMBINE,
        "How do I get to flagged stations?",
        "Click {nav.mocks}, then open the Flagged Stations tab at the top.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "what-flagged",
        COMBINE,
        "What are flagged stations?",
        "Flagged stations are cases you marked during a mock so you can find them again for review or extra practice.",
    ),
    FaqEntry(
        "flag-station",
        COMBINE,
        "How do I flag a station?",
        "During your session, use the flag icon near the station indicator at the top of the page to mark that station.",
    ),
    FaqEntry(
        "review-flagged",
        COMBINE,
        "How do I review a flagged station?",
        "Go to {nav.mocks}, Flagged Stations tab, then use View Details on the station you want.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "flag-duration",
        COMBINE,
        "How long do stations stay flagged?",
        "They stay flagged until you remove the flag yourself.",
    ),
    FaqEntry(
        "new-attempt",
        ACTIONS,
        "How do I start a new attempt for a station I did before?",
        "Click {nav.mocks}, Setup tab, View All Sessions, open your session, then click Start New Attempt on the station you want.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "retry-station",
        ACTIONS,
        "How do I retry a station?",
        "Open the session from View All Sessions, find the station, and click Start New Attempt.",
    ),
    FaqEntry(
        "review-last-attempt",
        ACTIONS,
        "How do I review my last attempt?",
        "Click {nav.mocks}, View All Sessions, open your session, then click Review Last Attempt for that station.",
        _MOCKS_NAV,
    ),
    FaqEntry(
        "open-completed",
        ACTIONS,
        "How do I open a station I already completed?",
        "From View All Sessions, select your session, then use Review Last Attempt to see feedback and transcript, or Start New Attempt for another go.",
    ),
    FaqEntry(
        "attempts-per-station",
        ACTIONS,
        "How many attempts do I get per station?",
        "Each station allows a maximum of three attempts. After three, Start New Attempt is blocked for that station. If a glitch used an attempt without a real consultation, open {nav.messages} and include the session and station names so support can reset it.",
    ),
    FaqEntry(
        "reattempt-after-three",
        ACTIONS,
        "How do I reattempt a station after three attempts?",
        "You cannot reset attempts yourself. After three attempts the station is finished for that access period. Use {nav.messages} only if technical failures burned attempts you could not complete.",
    ),
    FaqEntry(
        "reset-all",
        ACTIONS,
        "How do I reset all stations and start again?",
        "There is no self serve full reset button. Create a new session from {nav.mocks} Setup for fresh practice. For attempts due to technical issues, use {nav.messages} with session and station names.",
        _MOCKS_NAV,
    ),
)
