"""PLAB, CASC and orthodontics overlays: their own onboarding scenes and exam-specific answers."""

from __future__ import annotations

from ..models import FaqEntry, OnboardingScene
from ..overlay import Overlay
from .base_station import STATION

ORTHO_CV = "Orthodontics CV"

PLAB_OVERLAY = Overlay(
    onboarding_scenes=(
        OnboardingScene(
            "Hello doctor, I've been getting chest tightness when I climb the stairs at home.",
            "How do you open the consultation and explore the presenting complaint?",
        ),
        OnboardingScene(
            "My dad died of a heart attack at fifty. I keep thinking this is the same thing.",
            "The patient has shared a fear and a family history. How do you respond?",
        ),
        OnboardingScene(
            "So what happens now, doctor?", "How do you explain the plan and safety net clearly?"
        ),
    ),
)

CASC_OVERLAY = Overlay(
    onboarding_scenes=(
        OnboardingScene(
            "I don't really see the point of being here. Nothing is going to change.",
            "How do you open the interview and build rapport?",
        ),
        OnboardingScene(
            "Some nights I just lie there and think everyone would be better off without me.",
            "The patient has disclosed possible suicidal ideation. How do you respond and explore risk?",
        ),
        OnboardingScene(
            "What are you going to do with what I've told you?",
            "How do you explain next steps and close the interview safely?",
        ),
    ),
)

ORTHO_OVERLAY = Overlay(
    onboarding_scenes=(
        OnboardingScene(
            "Hi, I'm here because my dentist said my teeth are crowded and I might need braces.",
            "How do you open the consultation and establish the patient's concerns?",
        ),
        OnboardingScene(
            "I'm worried braces will look awful and I've got my exams this year.",
            "The patient raises appearance and timing concerns. How do you respond?",
        ),
        OnboardingScene(
            "So what are my options?", "How do you outline treatment options and agree next steps?"
        ),
    ),
    replace=(
        FaqEntry(
            "role-reversal",
            STATION,
            "Can I practice role reversals?",
            "On the orthodontics track the debrief modal offers Debrief Session only. Practice as Patient is not available here.",
        ),
        FaqEntry(
            "practice-as-patient",
            STATION,
            "What is Practice as Patient?",
            "Practice as Patient is not offered on the orthodontics track. Use Debrief Session from the Feedback tab to review your performance with Athena.",
        ),
        FaqEntry(
            "doctor-mode-unavailable",
            STATION,
            "Athena Doctor mode or Practice as Patient is not available",
            "Practice as Patient is hidden on the orthodontics track by design. Complete a station, wait for feedback, then use Start Debrief and Debrief Session.",
        ),
        FaqEntry(
            "debrief-session",
            STATION,
            "What happens in a debrief session?",
            "Start Debrief opens a modal where you pick Debrief Session to talk through your performance with Athena.",
        ),
    ),
    add=(
        FaqEntry(
            "ortho-upload-cv",
            ORTHO_CV,
            "How do I upload my CV for ortho?",
            "You can upload a PDF from {nav.settings}, Profile tab, using the Upload CV button. Onboarding may also prompt you from the dashboard modal when first setting up.",
            ("settings",),
        ),
        FaqEntry(
            "ortho-onboarding",
            ORTHO_CV,
            "Where is ortho onboarding?",
            "The dashboard can open an onboarding modal for steps such as CV upload. You can also manage your CV from {nav.settings} under Profile.",
            ("settings",),
        ),
    ),
)
