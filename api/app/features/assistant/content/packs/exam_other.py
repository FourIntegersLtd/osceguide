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
            replies=(
                "Hello, I'm one of the doctors. Can you tell me more about this tightness?",
                "Is it a sharp pain or a dull pain?",
                "That's probably just being a bit out of shape.",
            ),
            model_answer='"Hello, I\'m one of the doctors here. Tell me about the tightness: when did you first notice it, and what is it like?" Start open, then focus on onset, character and what brings it on.',
        ),
        OnboardingScene(
            "My dad died of a heart attack at fifty. I keep thinking this is the same thing.",
            "The patient has shared a fear and a family history. How do you respond?",
            replies=(
                "I'm so sorry about your dad. It makes sense this is on your mind. What worries you most?",
                "Your heart is probably fine, don't worry.",
                "How old are you now?",
            ),
            model_answer="\"I'm sorry about your dad. No wonder this is frightening. Let's look into it properly together. What worries you most?\" Acknowledge the fear, then explore it.",
        ),
        OnboardingScene(
            "So what happens now, doctor?",
            "How do you explain the plan and safety net clearly?",
            replies=(
                "I'd like to do a heart tracing and some blood tests today. If the tightness comes on at rest or won't settle, call 999. Does that sound okay?",
                "We'll do some tests.",
                "You need a troponin and an exercise tolerance test to exclude ACS.",
            ),
            model_answer="\"I'd like to do a heart tracing and blood tests today, and refer you to the chest pain clinic. If the tightness comes on at rest or doesn't settle within a few minutes, call 999. What questions do you have?\" Plain language, a clear plan and a safety net.",
        ),
    ),
)

CASC_OVERLAY = Overlay(
    onboarding_scenes=(
        OnboardingScene(
            "I don't really see the point of being here. Nothing is going to change.",
            "How do you open the interview and build rapport?",
            replies=(
                "It sounds like things feel pretty hopeless right now. Would you tell me what's been happening?",
                "Well, you're here now, so let's get through the questions.",
                "Lots of people feel like that. It will get better.",
            ),
            model_answer="\"It sounds like you're feeling pretty hopeless at the moment, and I appreciate you coming in anyway. Can you tell me a bit about what's been going on?\" Reflect the feeling and invite their story.",
        ),
        OnboardingScene(
            "Some nights I just lie there and think everyone would be better off without me.",
            "The patient has disclosed possible suicidal ideation. How do you respond and explore risk?",
            replies=(
                "Thank you for telling me. When you have those thoughts, do you ever think about ending your life?",
                "Don't say that. Your family would be devastated.",
                "Let's move on and talk about your sleep.",
            ),
            model_answer='"Thank you for trusting me with that. It sounds like you\'re in a lot of pain. When you have those thoughts, have you thought about ending your life, or made any plans?" Asking directly does not raise the risk; it opens a proper risk assessment.',
        ),
        OnboardingScene(
            "What are you going to do with what I've told you?",
            "How do you explain next steps and close the interview safely?",
            replies=(
                "What you've told me stays within your care team, unless I'm worried about your safety, and then I'd talk to you first. Shall we plan the next steps together?",
                "I'll have to tell everyone, I'm afraid.",
                "Don't worry about that.",
            ),
            model_answer="\"That's a fair question. What you share stays within your care team. If I'm worried about your safety, I'll talk with you about who else needs to know. Let's agree a plan together, including who to contact if things get worse.\" Be honest about confidentiality, plan jointly and safety-net.",
        ),
    ),
)

ORTHO_OVERLAY = Overlay(
    onboarding_scenes=(
        OnboardingScene(
            "Hi, I'm here because my dentist said my teeth are crowded and I might need braces.",
            "How do you open the consultation and establish the patient's concerns?",
            replies=(
                "Hello, nice to meet you. What do you notice about your teeth, and what would you like to change?",
                "Let me have a look at your bite first.",
                "You'll definitely need braces then.",
            ),
            model_answer='"Hello, nice to meet you. Your dentist mentioned crowding. What do you notice about your teeth, and what are you hoping for?" Start with the patient\'s own concerns before the examination.',
        ),
        OnboardingScene(
            "I'm worried braces will look awful and I've got my exams this year.",
            "The patient raises appearance and timing concerns. How do you respond?",
            replies=(
                "That's a really common worry. There are less visible options, and we can plan around your exams. What matters most to you?",
                "They're not that noticeable, honestly.",
                "Treatment usually takes eighteen to twenty-four months.",
            ),
            model_answer="\"That's a completely understandable worry, especially in an exam year. Let's talk about how visible the different options are and when it would be best to start. What would make this easier for you?\" Validate the concern, then involve them in the decision.",
        ),
        OnboardingScene(
            "So what are my options?",
            "How do you outline treatment options and agree next steps?",
            replies=(
                "There are a few options: fixed braces, clear aligners, or waiting and monitoring. I'll explain each, then we can decide together.",
                "Fixed braces are the best option.",
                "We could correct the class II with a functional appliance.",
            ),
            model_answer='"You have a few options: fixed braces, clear aligners, or monitoring for now. I\'ll explain the pros and cons of each and give you written information, and we can decide together at your next visit. What questions do you have?" Options in plain language, a shared decision and a clear next step.',
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
