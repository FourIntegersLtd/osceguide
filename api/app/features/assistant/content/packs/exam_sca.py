"""SCA overlay: colleague practice, Marketplace, A to Z, Slides, Consultation Tips, RAG scores."""

from __future__ import annotations

from ..models import FaqEntry, OnboardingScene
from ..overlay import Overlay
from .base_navigation import NAVIGATION
from .base_practice import SETUP
from .base_progress import DASHBOARD, SCORES

COLLEAGUES = "Practice with colleagues"
RECOMMENDATIONS = "Recommendations"

ONBOARDING_SCENES = (
    OnboardingScene(
        "Hi doctor, I've had this headache for a few days and it's not going away.",
        "How do you open the consultation?",
        replies=(
            "Hello, I'm one of the doctors. Tell me about this headache.",
            "How bad is the pain out of ten?",
            "Headaches are usually nothing serious, so try not to worry.",
        ),
        model_answer="\"Hello, I'm one of the doctors today. I'm sorry the headache has been bothering you. Can you tell me about it from the beginning?\" An open question lets the patient tell their story before you narrow down.",
    ),
    OnboardingScene(
        "I've just been so worried about what this could be. My mother had a brain tumour.",
        "The patient is offering an emotional cue and their core concern. How do you respond?",
        replies=(
            "That sounds really frightening, especially after what happened to your mum. What's worrying you most?",
            "Brain tumours are very rare, so I'm sure it's nothing.",
            "Is the headache worse in the mornings?",
        ),
        model_answer='"That must be really worrying, given what your mother went through. Can you tell me more about what\'s on your mind?" Name the fear and invite them to say more before you reassure.',
    ),
    OnboardingScene(
        "Okay, so what should I do now?",
        "How do you close the loop and provide clear next steps?",
        replies=(
            "Let's agree a plan together, and I'll tell you which warning signs mean you should come back sooner.",
            "Take some painkillers and see how you go.",
            "We'll need to rule out a space-occupying lesion with neuroimaging.",
        ),
        model_answer='"Here\'s what I suggest: simple pain relief, a headache diary and a review in two weeks. If you get a sudden severe headache, weakness or repeated vomiting, get help straight away. Does that plan work for you?" Clear steps, a safety net, and checking they agree.',
    ),
)

OVERLAY = Overlay(
    onboarding_scenes=ONBOARDING_SCENES,
    replace=(
        FaqEntry(
            "practice-tabs",
            SETUP,
            "What are the tabs on the AI Practice page?",
            "Setup is where you create sessions and open View All Sessions. Combine Stations builds a session from stations you already attempted. Flagged Stations lists cases you marked with a flag. You also have Consultation Tips with guidance content.",
            ("mocks",),
        ),
        FaqEntry(
            "focus-improving",
            DASHBOARD,
            "What should I focus on improving?",
            "Open {nav.dashboard} and read the Important Observations section and the recommendation panel. Then practise the suggested skill in {nav.mocks}.",
            ("dashboard", "mocks"),
        ),
        FaqEntry(
            "score-x-of-y",
            SCORES,
            "What does a score like 7 of 11 mean?",
            "It means seven skills were Green or Amber out of eleven assessed in that area, leaving four Red.",
        ),
    ),
    add=(
        FaqEntry(
            "nav-marketplace",
            NAVIGATION,
            "Where is the Marketplace?",
            "Click {nav.marketplace} in the left navigation. It is used to post or book scheduled practice with colleagues.",
            ("marketplace",),
        ),
        FaqEntry(
            "nav-a-to-z",
            NAVIGATION,
            "Where is A to Z?",
            "Click {nav.summary} in the left navigation. It is reference content organised alphabetically.",
            ("summary",),
        ),
        FaqEntry(
            "a-to-z-notes",
            NAVIGATION,
            "Can I add my own notes in A to Z?",
            "{nav.summary} is reference content. There is no built in personal notes editor on those pages. Use your own notes app alongside it, or use {nav.messages} for feature requests.",
            ("summary",),
        ),
        FaqEntry(
            "nav-slides",
            NAVIGATION,
            "Where are Slides?",
            "Click {nav.slides} in the left navigation.",
            ("slides",),
        ),
        FaqEntry(
            "consultation-tips",
            SETUP,
            "What is Consultation Tips?",
            "Consultation Tips is a tab under {nav.mocks} with extra guidance material. It does not replace doing a live station.",
            ("mocks",),
        ),
        FaqEntry(
            "hypothesis-content",
            SETUP,
            "Where is Consultation Tips or the hypothesis content?",
            "Open {nav.mocks} and select the Consultation Tips tab. That is where consultation skill guidance lives. It is separate from running a live station on Simulation.",
            ("mocks",),
        ),
        FaqEntry(
            "important-observations",
            DASHBOARD,
            "Where are important observations?",
            "Important Observations is a section on {nav.dashboard}, next to the recommendations panel.",
            ("dashboard",),
        ),
        FaqEntry(
            "recommendation-system",
            RECOMMENDATIONS,
            "How does the recommendation system work?",
            "The dashboard recommendations first highlight regressions, then stagnations, then if neither applies they fall back to your lowest scoring skill.",
        ),
        FaqEntry(
            "recommendation-priority",
            RECOMMENDATIONS,
            "How are skills prioritized in recommendations?",
            "The focus skill picks the worst regression if any exist, otherwise the worst stagnation, otherwise the lowest score. Alternative skills get higher priority when drops are larger, scores are lower, or a skill appears in more than one list.",
        ),
        FaqEntry(
            "recommendation-benefits",
            RECOMMENDATIONS,
            "What benefits do recommendations give me?",
            "You get a primary focus skill plus alternative skills to choose from, driven by your recent data.",
        ),
        FaqEntry(
            "why-this-skill",
            RECOMMENDATIONS,
            "Why is Athena suggesting this skill?",
            "Open {nav.dashboard} and read the recommendations area next to Important Observations. It explains the regression, stagnation, or low score behind the suggestion.",
            ("dashboard",),
        ),
        FaqEntry(
            "rag-meaning",
            SCORES,
            "What do Red, Amber, and Green scores mean?",
            "On station feedback, skills are shown with Red, Amber, and Green levels. Green means strong, Amber means acceptable with room to grow, Red means needs work. Green and Amber are both treated as satisfactory in summaries like X out of Y skills.",
        ),
        FaqEntry(
            "rag-scoring",
            SCORES,
            "What is RAG scoring?",
            "RAG means Red, Amber, Green, the three colour levels used on skill breakdowns in feedback.",
        ),
        FaqEntry(
            "practice-with-colleague",
            COLLEAGUES,
            "How do I practice with a colleague?",
            "On {nav.dashboard}, click Practice with colleague, then pick Live Practice for an instant queue match, or use Schedule Practice to go to {nav.marketplace} for booked slots. After a mock you can also see Live Practice and Schedule Practice on the session end screen.",
            ("dashboard", "marketplace"),
        ),
        FaqEntry(
            "live-practice",
            COLLEAGUES,
            "What is Live Practice?",
            "Live Practice is started from Practice with colleague on {nav.dashboard} or from the session end screen. It places you in a queue to be matched with another user. The human practice UI recommends using a laptop.",
            ("dashboard",),
        ),
        FaqEntry(
            "marketplace-how",
            COLLEAGUES,
            "How does the Marketplace work?",
            "Open {nav.marketplace} from the left navigation to post availability or claim slots. Use the Upcoming Sessions tab to join booked sessions. Prefer a laptop for video sessions.",
            ("marketplace",),
        ),
        FaqEntry(
            "marketplace-join",
            COLLEAGUES,
            "How do I join a scheduled Marketplace session?",
            "Open {nav.marketplace}, then the Upcoming Sessions tab. You can join from twenty minutes before the scheduled start time until one hour after it. A popup may also appear when a session becomes joinable.",
            ("marketplace",),
        ),
        FaqEntry(
            "marketplace-too-early",
            COLLEAGUES,
            "Marketplace says too early even though it is my start time",
            "Confirm you are on Upcoming Sessions and within the join window starting twenty minutes before the booked time. Refresh the page and check your device clock. If it still says too early at the correct time, use {nav.messages} with the session time.",
            ("marketplace",),
        ),
        FaqEntry(
            "colleague-roles",
            COLLEAGUES,
            "How are doctor and patient roles assigned?",
            "Roles are assigned automatically when you join, with fairness so you experience both sides over time.",
        ),
        FaqEntry(
            "colleague-phone",
            COLLEAGUES,
            "Can I join on my phone?",
            "For colleague practice, use a laptop. Mobile does not support the full video and interaction experience.",
        ),
        FaqEntry(
            "partner-no-show",
            COLLEAGUES,
            "What if my partner does not show up?",
            "You can cancel from Upcoming Sessions if they do not join in time. Reminder emails for marketplace sessions are intended to go out about one hour before the scheduled start.",
            ("marketplace",),
        ),
    ),
)
