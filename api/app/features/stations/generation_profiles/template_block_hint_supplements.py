"""Plain-English generation hints for template field ids not in B2C-exported profiles."""

from __future__ import annotations

TEMPLATE_BLOCK_HINT_SUPPLEMENTS: dict[str, str] = {
    "capability": (
        "Which SCA clinical experience group this station tests. Pick one label from the "
        "standard list (e.g. mental health, older adults, prescribing). Write realistic "
        "content that fits that group."
    ),
    "management_examination_findings": (
        "Examination findings the candidate would expect after assessing the patient — "
        "vitals, focused exam, and anything that changes management. Write as clear "
        "bullet points, not shorthand only."
    ),
    "investigation_type": (
        "What kind of test or result the candidate is discussing (e.g. blood test, "
        "imaging). Keep it specific to the scenario."
    ),
    "recent_abnormal_results": (
        "The abnormal results the candidate must act on — values or wording a GP would "
        "see on a result letter or screen."
    ),
    "past_results_trend": (
        "How earlier results compare (stable, worsening, improving). Helps the candidate "
        "decide urgency and follow-up."
    ),
    "further_investigations": (
        "Tests or imaging to arrange next — bloods, scans, or referrals. Match the scenario "
        "and say why each test helps."
    ),
}
