"""Base FAQ: the station page (Simulation, Management, Feedback, debrief)."""

from __future__ import annotations

from ..models import FaqEntry

STATION = "Station page — Simulation, Management, Feedback"

_M = ("mocks",)

ENTRIES: tuple[FaqEntry, ...] = (
    FaqEntry(
        "management-plan-path",
        STATION,
        "Where can I find my management plan for a station?",
        "Click {nav.mocks}, View All Sessions, open your session, click Review Last Attempt, then open the Management tab at the top.",
        _M,
    ),
    FaqEntry(
        "management-plan",
        STATION,
        "Where is the management plan?",
        "After Review Last Attempt, use the Management tab on the station page.",
    ),
    FaqEntry(
        "see-feedback",
        STATION,
        "How do I see my feedback?",
        "Click {nav.mocks}, View All Sessions, open your session, click Review Last Attempt, then open the Feedback tab at the top.",
        _M,
    ),
    FaqEntry(
        "athena-feedback",
        STATION,
        "Where is my Athena feedback?",
        "Open Review Last Attempt for the station, then go to the Feedback tab.",
    ),
    FaqEntry(
        "transcript-path",
        STATION,
        "Where is the consultation transcript?",
        "Click {nav.mocks}, View All Sessions, open your session, click Review Last Attempt, then open the Simulation tab. The Simulation screen shows the consultation area and a Transcription panel: on large screens the transcription is beside the consultation; on small screens it stacks below.",
        _M,
    ),
    FaqEntry(
        "what-i-said",
        STATION,
        "Where can I read what I said to the patient?",
        "Go to Review Last Attempt, then the Simulation tab. The transcription list is in the Transcription panel on that screen.",
    ),
    FaqEntry(
        "simulation-chat",
        STATION,
        "How do I see the chat from my simulation?",
        "Use Review Last Attempt, then the Simulation tab. Your messages appear in the Transcription panel.",
    ),
    FaqEntry(
        "transcript-tab",
        STATION,
        "Which tab has the transcript?",
        "The Simulation tab. Feedback and Management tabs do not replace it.",
    ),
    FaqEntry(
        "start-consultation",
        STATION,
        "How do I start the consultation?",
        "In attempt mode, open the Simulation tab. The top tab label may read Start Simulation until you are in the simulation view. Press the Start Consultation button in the consultation panel to begin the timed case.",
    ),
    FaqEntry(
        "ai-patient-answers",
        STATION,
        "Does the AI patient answer my questions?",
        "Yes. After Start Consultation, speak as you would to a real patient. The AI patient responds by voice. Ask normal consultation questions. If you get no reply, check microphone permission and remember to use Chrome on a laptop for the best audio experience.",
    ),
    FaqEntry(
        "simulation-tab",
        STATION,
        "What is the Simulation tab?",
        "Simulation is where you run or review the live consultation and see the Transcription panel for that attempt.",
    ),
    FaqEntry(
        "patient-not-responding",
        STATION,
        "The patient or AI is not responding but the timer is running",
        "Stop and refresh the page rather than letting the timer burn an attempt. Allow microphone access, use Chrome or Edge on a laptop, check that the correct mic is selected, and start the consultation again. If voice still fails, leave the station and use {nav.messages} with the session and station names so attempts can be reviewed.",
    ),
    FaqEntry(
        "cannot-hear-ai",
        STATION,
        "I cannot hear the AI when I start consultation",
        "Check speaker volume and that the browser is not muted, then refresh and try Start Consultation again on Chrome or Edge. Headphones sometimes help. If it keeps failing, use {nav.messages}.",
    ),
    FaqEntry(
        "debrief",
        STATION,
        "How do I debrief with Athena?",
        "Click {nav.mocks}, View All Sessions, open your session, Review Last Attempt, Feedback tab, then click Start Debrief to talk with Athena about your performance.",
        _M,
    ),
    FaqEntry(
        "debrief-stuck",
        STATION,
        "Athena debrief stays on connecting and never speaks",
        "Refresh the page, confirm microphone permission, and try Start Debrief again from the Feedback tab. Use a laptop browser when possible. If it still sticks on connecting, use {nav.messages} with the session name.",
    ),
    FaqEntry(
        "role-reversal",
        STATION,
        "Can I practice role reversals?",
        "After feedback is available, click Start Debrief in the Feedback tab. In the modal, choose Practice as Patient so Athena acts as the doctor and you as the patient.",
    ),
    FaqEntry(
        "practice-as-patient",
        STATION,
        "What is Practice as Patient?",
        "It is the second option in the debrief modal: Athena runs the consultation as the doctor while you experience it as the patient. The UI labels this mode Doctor Mode while it is active.",
    ),
    FaqEntry(
        "doctor-mode-unavailable",
        STATION,
        "Athena Doctor mode or Practice as Patient is not available",
        "Complete a station attempt first and wait until feedback is ready. Open Review Last Attempt, Feedback tab, then Start Debrief and choose Practice as Patient.",
    ),
    FaqEntry(
        "debrief-session",
        STATION,
        "What happens in a debrief session?",
        "Start Debrief opens a modal where you pick Debrief Session to talk through your performance with Athena, or Practice as Patient to hear Athena model the doctor side.",
    ),
    FaqEntry(
        "feedback-generating",
        STATION,
        "Feedback is still generating. What do I do?",
        "Stay on the station page. When feedback is ready, you will get a notification and can open the Feedback tab. If it takes unusually long, try refreshing after a few minutes or use {nav.messages}.",
    ),
    FaqEntry(
        "no-feedback-or-transcript",
        STATION,
        "I finished a station but there is no feedback or transcript",
        "Open {nav.mocks}, View All Sessions, open the session, then Review Last Attempt. Check Feedback for scores and Simulation for the transcript. Wait a few minutes if generation is still running. If Review Last Attempt is missing or says page not found, use {nav.messages} with the session and station names.",
        _M,
    ),
    FaqEntry(
        "attempt-not-saved",
        STATION,
        "The attempt did not save or Review Last Attempt is missing",
        "Refresh and reopen the session from View All Sessions. If the station still shows no usable attempt or feedback after a completed consultation, use {nav.messages} and include session name, station name, and roughly when you practised.",
    ),
)
