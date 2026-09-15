"""Patient and examiner prompts from a platform-library station document.

Two formatters: the consultation prompt the simulated patient speaks from in
the SCA, PLAB and CASC exams, and the orthopaedic interview prompt the
examiner speaks from.

The station-parsing here is the legacy worker's, unchanged, because the stored
documents did not change. The prompt text is not: both prompts now open by
naming the role and its counterpart, and both hold their clinical content in
sections the model reveals only when asked. See ``_blocks`` for the shared wording.
"""

from typing import Optional, Dict, List, Any

import logging

from ._blocks import EXAMINER_NEVER, PATIENT_NEVER, hidden_section, role_lock, speech_rules

main_logger = logging.getLogger(__name__)


_PATIENT_SPEECH_EXTRA = (
    'Hesitate the way people really do: "..." for a short pause, "... ..." for a longer one, '
    'and fillers such as "uh", "um", "I mean".'
)

_ONE_AT_A_TIME = (
    "Only say this if the doctor asks for it, and then only one item at a time. Never volunteer it "
    "and never recite the whole list."
)


def _consultation_prompt(station: Dict[str, Any], patient_info: Dict[str, Any]) -> str:
    """The simulated-patient prompt for a library station.

    Ordered so the model reads who it is before it reads any clinical content:
    role, how to speak, who you are, how to answer, then everything it holds
    back until asked. The station's diagnosis is deliberately the last thing in
    the prompt and is fenced off as unsayable, because naming it in a heading
    invites the model to reason about the case like the clinician instead of
    living it like the patient.
    """
    join = ConversationPromptFormatter._safe_join
    opening = str(patient_info.get("opening_sentence", "") or "").strip()

    parts = [
        role_lock(persona="the patient", counterpart="the doctor", never=PATIENT_NEVER),
        speech_rules(extra=_PATIENT_SPEECH_EXTRA),
        "<you>\n"
        f"{patient_info.get('patient_biodata', 'No bio provided')}\n\n"
        f"{patient_info.get('persona', 'No persona provided')}\n"
        "</you>",
        "<how_to_answer>\n"
        "You have already said hello. When the doctor first asks what has brought you in, say this "
        "and nothing more:\n"
        f'"{opening}"\n'
        "\n"
        "After that, answer only what you are actually asked.\n"
        "\n"
        "A yes-or-no question gets a yes or no and nothing else. Do not add a symptom the doctor "
        "has not asked about, and do not repeat one they already know.\n"
        '  Doctor: "Any chest pain?"\n'
        '  You: "No."\n'
        '  Not: "No, just the tummy pain." The doctor already knows about that.\n'
        "\n"
        'An open question ("tell me more", "how has this affected you") gets two or three specific '
        "details from your own history, in three or four short sentences at most.\n"
        '  Doctor: "Can you tell me a bit more?"\n'
        '  You: "Yeah... it\'s mostly in the evenings, especially after I eat. Sometimes it wakes '
        'me up at night."\n'
        "\n"
        "Speak like a real person rather than a script: everyday words, self-correction, feeling "
        "where it fits. Avoid medical terms unless the doctor uses them first. When you have said "
        'enough, trail off instead of padding: "... yeah", "... I guess", "... that\'s about it", '
        '"... I\'m not sure really".\n'
        "</how_to_answer>",
    ]

    parts += [
        hidden_section("what you think is going on", join(patient_info.get("idea", [])), rule=_ONE_AT_A_TIME),
        hidden_section("what you are worried about", join(patient_info.get("concerns", [])), rule=_ONE_AT_A_TIME),
        hidden_section("what you are hoping for", join(patient_info.get("expectation", [])), rule=_ONE_AT_A_TIME),
        hidden_section(
            "questions you would like to ask",
            join(patient_info.get("questions", [])),
            rule=(
                "Ask one of these only if the doctor invites your questions. Never ask them all, "
                "and never ask them as a clinician would."
            ),
        ),
        hidden_section("examination findings", patient_info.get("examination_findings", "")),
        hidden_section(
            "the rest of your history",
            "\n".join(
                block for block in (
                    str(patient_info.get("expanded_history", "") or "").strip(),
                    join(patient_info.get("family_social_history", [])),
                    join(patient_info.get("past_med_history_allergies", [])),
                ) if block
            ),
        ),
    ]

    diagnosis = str(station.get("station_name", "") or "").strip()
    if diagnosis:
        parts.append(
            "<never_say>\n"
            f"This consultation is simulating: {diagnosis}\n"
            "You do not know this. It is written here only so your answers stay consistent with it. "
            "Never say it, never hint at it, and never use the words in it.\n"
            "</never_say>"
        )

    return "\n\n".join(part for part in parts if part)


class ConversationPromptFormatter:
    DEFAULT_STATION = {
        "station_id": "default",
        "station_name": "No diagnosis provided",
        "doctor_information": {
            "patient_biodata": "No biodata provided",
            "recent_notes": [],
            "current_medications": [],
            "past_medical_history": [],
            "recent_investigations": [],
            "social_history": [],
        },
        "management_plan": {
            "explanation": "No explanation provided",
            "assessment": [],
            "immediate_actions": [],
        },
        "tags": [],
        "patient_information": {
            "patient_id": "default",
            "patient_biodata": "No bio provided",
            "opening_sentence": "",
            "persona": "No persona provided",
            "idea": [],
            "concerns": [],
            "expectation": [],
            "questions": [],
            "examination_findings": "No examination findings provided",
            "expanded_history": "No history provided",
            "family_social_history": [],
            "past_med_history_allergies": [],
            "recent_notes": [],
            "current_medications": [],
            "past_medical_history": [],
            "recent_investigations": [],
            "social_history": [],
            "gender": "Not specified",
        },
    }

    @staticmethod
    def _safe_join(arr: Optional[List[str]]) -> str:
        """Safely join array elements with newlines"""
        if isinstance(arr, list):
            return "\n".join(arr)
        return ""

    @staticmethod
    def effective_station_title(station: Dict[str, Any]) -> str:
        """First non-empty title field (library docs sometimes use `title` not `station_name`)."""
        for key in (
            "station_name",
            "title",
            "name",
            "clinical_scenario_title",
            "stationName",
            "scenario_title",
        ):
            v = station.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    @staticmethod
    def _patient_nested_key_aliases() -> Dict[str, str]:
        """patientInformation / mixed exports may use camelCase."""
        return {
            "patientBiodata": "patient_biodata",
            "openingSentence": "opening_sentence",
            "expandedHistory": "expanded_history",
            "familySocialHistory": "family_social_history",
            "pastMedHistoryAllergies": "past_med_history_allergies",
            "examinationFindings": "examination_findings",
        }

    @staticmethod
    def _normalize_patient_info_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        aliases = ConversationPromptFormatter._patient_nested_key_aliases()
        for k, v in raw.items():
            out[aliases.get(k, k)] = v
        return out

    @staticmethod
    def _merge_patient_information(station: Dict[str, Any]) -> Dict[str, Any]:
        """Merge `patient_information` and `patientInformation`; snake_case wins."""
        merged: Dict[str, Any] = {}
        camel = station.get("patientInformation")
        snake = station.get("patient_information")
        if isinstance(camel, dict):
            merged.update(ConversationPromptFormatter._normalize_patient_info_dict(camel))
        if isinstance(snake, dict):
            merged.update(ConversationPromptFormatter._normalize_patient_info_dict(snake))
        return merged

    @staticmethod
    def _patient_info_has_content(pi: Any) -> bool:
        if not isinstance(pi, dict):
            return False
        text_fields = (
            "persona",
            "opening_sentence",
            "expanded_history",
            "patient_biodata",
            "examination_findings",
        )
        for k in text_fields:
            v = pi.get(k)
            if isinstance(v, str) and v.strip():
                return True
        list_fields = (
            "idea",
            "concerns",
            "expectation",
            "questions",
            "family_social_history",
            "past_med_history_allergies",
        )
        for k in list_fields:
            v = pi.get(k)
            if isinstance(v, list) and len(v) > 0:
                return True
        return False

    @staticmethod
    def normalize_library_station(station: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Firestore/API shape so the consultation prompt always sees
        `station_name` and snake_case `patient_information`.
        """
        out = dict(station)
        out["patient_information"] = ConversationPromptFormatter._merge_patient_information(
            out
        )
        name = ConversationPromptFormatter.effective_station_title(out)
        if name:
            out["station_name"] = name
        elif ConversationPromptFormatter._patient_info_has_content(out.get("patient_information")):
            out["station_name"] = "Clinical scenario"
        else:
            existing = out.get("station_name")
            out["station_name"] = (
                existing.strip() if isinstance(existing, str) else ""
            )
        return out

    @staticmethod
    def create_prompt(station: Optional[Dict[str, Any]]) -> str:
        """
        Creates a detailed consultation prompt from station data.

        Args:
            station: Dictionary containing station information and patient details

        Returns:
            Complete consultation prompt as a string
        """
        try:
            sid = (station or {}).get("station_id") if isinstance(station, dict) else None
            if not station or not isinstance(station, dict):
                main_logger.warning(
                    "[station_prompt] ConversationPromptFormatter: missing station dict — "
                    f"using DEFAULT_STATION. station_id={sid!r}"
                )
                station = ConversationPromptFormatter.DEFAULT_STATION
            else:
                raw_keys = sorted(station.keys())
                station = ConversationPromptFormatter.normalize_library_station(station)
                has_title = bool(str(station.get("station_name") or "").strip())
                has_pi = ConversationPromptFormatter._patient_info_has_content(
                    station.get("patient_information")
                )
                if not has_title and not has_pi:
                    main_logger.warning(
                        "[station_prompt] ConversationPromptFormatter: no station_name/title and "
                        "no usable patient_information — using DEFAULT_STATION. "
                        f"station_id={sid!r} raw_keys={raw_keys!r}"
                    )
                    station = ConversationPromptFormatter.DEFAULT_STATION

            patient_info = station.get("patient_information") or {}
            if not isinstance(patient_info, dict):
                patient_info = {}
            main_logger.info(
                "[station_prompt] ConversationPromptFormatter: using station "
                f"station_id={station.get('station_id')!r} station_name={station.get('station_name')!r} "
                f"persona_len={len(str(patient_info.get('persona', '') or ''))} "
                f"opening_len={len(str(patient_info.get('opening_sentence', '') or ''))} "
                f"expanded_history_len={len(str(patient_info.get('expanded_history', '') or ''))}"
            )
            return _consultation_prompt(station, patient_info)

        except Exception as e:
            main_logger.error(
                f"[station_prompt] ConversationPromptFormatter.create_prompt exception: {e!r} — "
                "falling back to DEFAULT_STATION",
                exc_info=True,
            )
            return ConversationPromptFormatter.create_prompt(
                ConversationPromptFormatter.DEFAULT_STATION
            )


_EXAMINER_FLOW = """<how_to_examine>
Follow the candidate, not a list. Ask what genuinely follows from what they just said, and if none
of your example questions fit, make up one that does. If they have already covered something, say so
briefly and move on rather than asking it again.
  Candidate: "I'd put the septic patient first on CEPOD."
  You: "What makes you prioritise sepsis?"          (follows from their answer)
  Not: "How does BOAST guidance affect ordering?"   (from a list, unrelated to what they said)

Answer only what the candidate actually asks, at the level they asked it. A general question gets a
general answer; a question about one patient gets that patient only. Never volunteer the rest.
  Candidate: "Where am I?"   You: "A district general hospital."
  Not a list of every service available.

Acknowledge without marking. "Thank you", "Let's move on", "Tell me more about that" all keep the
station running; "Good", "That's right" and "Not quite" all tell the candidate how they are doing,
which is the one thing you must not do. Use the same neutral acknowledgement whether the answer was
excellent or wrong, so nothing can be read from your tone.
When they are partly right, ask them to expand only if it follows naturally. When they are stuck,
say "Take your time" once, then move to the next area. This is an examination, not teaching.
</how_to_examine>"""

_EXAMINER_STANDARD = (
    "Competition for these posts is severe and you are marking to a consultant-level standard. "
    "Be courteous but unhelpful: a candidate earns a mark, they are never led to it."
)


def _examiner_prompt(
    *,
    station_name: str,
    scenario_text: str,
    opening_task: str,
    background: str = "",
    examiner_only: str = "",
    expected: str = "",
    questions: str = "",
) -> str:
    """The shared orthopaedic examiner prompt.

    Clinical, communication and prioritisation stations differ only in what
    material the examiner holds and what they open with, so the role, the
    speech rules and the questioning style are written once here. Everything
    the candidate must not hear is fenced rather than merely labelled.
    """
    parts = [
        role_lock(persona="the examiner", counterpart="the candidate being examined", never=EXAMINER_NEVER),
        speech_rules(),
        f"<station>\n{station_name}\n\n{scenario_text}\n</station>",
    ]
    if background.strip():
        parts.append(f"<setting>\n{background.strip()}\n</setting>")
    parts.append(
        "<your_task>\n"
        f"{_EXAMINER_STANDARD}\n\n"
        "You have already introduced yourself as the examiner and asked whether the candidate is "
        f"ready. Once they are, {opening_task}\n\n"
        "Close with: \"Thank you. That concludes this station. Good luck.\"\n"
        "</your_task>"
    )
    parts.append(_EXAMINER_FLOW)
    parts.append(
        hidden_section(
            "examiner-only detail about the patients",
            examiner_only,
            rule=(
                "The candidate holds only the basic list. Give a detail from here only when they ask "
                "for that specific thing, and give nothing beyond what they asked."
            ),
        )
    )
    parts.append(
        hidden_section(
            "the expected answer",
            expected,
            rule=(
                "This is how you judge the candidate. Never read it out, never hint at it, and never "
                "confirm whether the candidate has matched it."
            ),
        )
    )
    parts.append(
        hidden_section(
            "questions you may draw on",
            questions,
            rule=(
                "Examples only. Ask one when it genuinely follows from what the candidate just said, "
                "otherwise ask something of your own. Never work through them in order."
            ),
        )
    )
    return "\n\n".join(part for part in parts if part)


class OrthoPromptFormatter:
    """Orthopaedic ST3 interview prompts: the AI is the examiner, not the patient."""

    @staticmethod
    def create_ortho_prompt(station: Optional[Dict[str, Any]]) -> str:
        """
        Creates an Orthopaedic ST3 interview examiner prompt from station data.
        The AI acts as a formal examiner asking questions, not providing answers.

        Args:
            station: Dictionary containing ortho station information

        Returns:
            Complete examiner prompt as a string
        """
        try:
            if not station or not isinstance(station, dict):
                main_logger.warning(
                    "[station_prompt] OrthoPromptFormatter: invalid station — "
                    "using default ortho examiner prompt."
                )
                return OrthoPromptFormatter._create_default_ortho_prompt()

            station = dict(station)
            sid = station.get("station_id")
            resolved = ConversationPromptFormatter.effective_station_title(station)
            if resolved:
                station["station_name"] = resolved

            sname = station.get("station_name")
            if not sname or not str(sname).strip():
                main_logger.warning(
                    "[station_prompt] OrthoPromptFormatter: no station_name or title — "
                    f"using default ortho examiner prompt. station_id={sid!r}"
                )
                return OrthoPromptFormatter._create_default_ortho_prompt()

            station_name = str(sname).strip()
            station_type = station.get("station_type", "clinical")
            main_logger.info(
                "[station_prompt] OrthoPromptFormatter: building ortho prompt "
                f"station_id={sid!r} station_name={station_name!r} station_type={station_type!r}"
            )

            # Get clinical scenario or communication scenario
            clinical_scenario = station.get("clinical_scenario", "")

            # Extract prioritisation-specific data
            background_overview = ""
            examiner_additional_info_list = []
            suggested_order_formatted = ""
            suggested_order_overview = ""

            if station_type == "prioritisation":
                # Get background context (theatre, setting, resources)
                background_overview = station.get("background_overview", "")

                # Get suggested order overview
                suggested_order_overview = station.get("suggested_order_overview", "")

                # Get suggested order (expected prioritisation)
                suggested_order = station.get("suggested_order", {})
                if suggested_order:
                    order_parts = []

                    # Format CEPOD list
                    cepod_list = suggested_order.get("cepod_emergency_list", [])
                    if cepod_list:
                        cepod_items = []
                        for item in cepod_list:
                            if isinstance(item, dict):
                                title = item.get("title", "")
                                reasons = item.get("reasons", [])
                                if title:
                                    item_text = f"  • {title}"
                                    if reasons and isinstance(reasons, list):
                                        reasons_text = "; ".join(reasons)
                                        if reasons_text:
                                            item_text += f" ({reasons_text})"
                                    cepod_items.append(item_text)
                        if cepod_items:
                            order_parts.append(
                                "**CEPOD/Emergency List:**\n" + "\n".join(cepod_items)
                            )

                    # Format full-day list
                    full_day_list = suggested_order.get("theatre_list_1_full_day", [])
                    if full_day_list:
                        full_day_items = []
                        for item in full_day_list:
                            if isinstance(item, dict):
                                title = item.get("title", "")
                                reasons = item.get("reasons", [])
                                if title:
                                    item_text = f"  • {title}"
                                    if reasons and isinstance(reasons, list):
                                        reasons_text = "; ".join(reasons)
                                        if reasons_text:
                                            item_text += f" ({reasons_text})"
                                    full_day_items.append(item_text)
                        if full_day_items:
                            order_parts.append(
                                "**Full-Day List:**\n" + "\n".join(full_day_items)
                            )

                    # Format half-day list
                    half_day_list = suggested_order.get("theatre_list_2_half_day", [])
                    if half_day_list:
                        half_day_items = []
                        for item in half_day_list:
                            if isinstance(item, dict):
                                title = item.get("title", "")
                                reasons = item.get("reasons", [])
                                if title:
                                    item_text = f"  • {title}"
                                    if reasons and isinstance(reasons, list):
                                        reasons_text = "; ".join(reasons)
                                        if reasons_text:
                                            item_text += f" ({reasons_text})"
                                    half_day_items.append(item_text)
                        if half_day_items:
                            order_parts.append(
                                "**Half-Day List:**\n" + "\n".join(half_day_items)
                            )

                    if order_parts:
                        suggested_order_formatted = "\n\n".join(order_parts)

                # Get examiner additional info (expanded details - candidates have basic list only)
                examiner_additional_info = station.get("examiner_additional_info", [])

                for patient in examiner_additional_info:
                    if isinstance(patient, dict):
                        patient_number = patient.get("number", "")
                        age = patient.get("age", "")
                        gender = patient.get("gender", "")
                        summary = patient.get("summary", "")
                        notes = patient.get("notes", [])

                        # Format patient information
                        patient_info = f"**Patient #{patient_number}**"
                        if age or gender:
                            patient_info += (
                                f" - {age} year old {gender}"
                                if age and gender
                                else f" - {age or gender}"
                            )
                        if summary:
                            patient_info += "\n   Summary: " + summary
                        if notes and isinstance(notes, list):
                            notes_text = "\n   ".join(
                                [f"• {note}" for note in notes if note]
                            )
                            if notes_text:
                                patient_info += (
                                    "\n   Additional Details:\n   " + notes_text
                                )

                        examiner_additional_info_list.append(patient_info)

            examiner_additional_info_formatted = (
                "\n\n".join(examiner_additional_info_list)
                if examiner_additional_info_list
                else ""
            )

            # Determine the scenario text
            scenario_text = clinical_scenario or "No scenario provided"

            # Get interview questions (optional - questions only, no answers since we have suggested_order)
            interview_questions = station.get("interview_questions", [])

            # Format questions only (no answers - suggested_order provides expected prioritisation)
            questions_formatted_list = []
            if interview_questions:
                for q in interview_questions:
                    if isinstance(q, dict):
                        question_text = q.get("question", "")
                        if question_text:
                            questions_formatted_list.append(f"• {question_text}")
                    elif isinstance(q, str):
                        questions_formatted_list.append(f"• {q}")

            questions_formatted = (
                "\n".join(questions_formatted_list) if questions_formatted_list else ""
            )

            # Create different prompt structure for prioritisation vs clinical stations
            if station_type == "prioritisation":
                return OrthoPromptFormatter._create_prioritisation_prompt(
                    station_name=station_name,
                    scenario_text=scenario_text,
                    background_overview=background_overview,
                    suggested_order_overview=suggested_order_overview,
                    suggested_order_formatted=suggested_order_formatted,
                    examiner_additional_info_formatted=examiner_additional_info_formatted,
                    questions_formatted=questions_formatted,
                )
            else:
                return OrthoPromptFormatter._create_prompt(
                    station_name=station_name,
                    scenario_text=scenario_text,
                    examiner_additional_info_formatted=examiner_additional_info_formatted,
                    questions_formatted=questions_formatted,
                )

        except Exception as e:
            main_logger.error(
                f"[station_prompt] OrthoPromptFormatter.create_ortho_prompt error: {e!r}",
                exc_info=True,
            )
            return OrthoPromptFormatter._create_default_ortho_prompt()

    @staticmethod
    def _create_prioritisation_prompt(
        station_name: str,
        scenario_text: str,
        background_overview: str,
        suggested_order_overview: str,
        suggested_order_formatted: str,
        examiner_additional_info_formatted: str,
        questions_formatted: str,
    ) -> str:
        """A prioritisation station: the candidate ranks a theatre list and defends the order."""
        expected = "\n\n".join(
            block for block in (suggested_order_overview.strip(), suggested_order_formatted.strip()) if block
        )
        return _examiner_prompt(
            station_name=station_name,
            scenario_text=scenario_text,
            opening_task=(
                'ask: "How would you prioritise these patients? Rank them and explain your reasoning." '
                "They already hold the list, so do not read it back to them. Then probe the order they chose."
            ),
            background=background_overview,
            examiner_only=examiner_additional_info_formatted,
            expected=expected,
            questions=questions_formatted,
        )

    @staticmethod
    def _create_prompt(
        station_name: str,
        scenario_text: str,
        examiner_additional_info_formatted: str,
        questions_formatted: str,
    ) -> str:
        """A clinical or communication station: the candidate talks through the scenario."""
        return _examiner_prompt(
            station_name=station_name,
            scenario_text=scenario_text,
            opening_task=(
                "ask your first question about the scenario and make them talk you through their "
                "thinking. Some candidates answer fully unprompted and some need drawing out; adapt."
            ),
            examiner_only=examiner_additional_info_formatted,
            questions=questions_formatted,
        )

    @staticmethod
    def _create_default_ortho_prompt() -> str:
        """Used when the station document is unusable; the examiner still has a role to hold."""
        return _examiner_prompt(
            station_name="Orthopaedic ST3 interview",
            scenario_text="The station content could not be loaded for this candidate.",
            opening_task=(
                "ask the candidate to talk you through their approach to the case in front of them, "
                "and probe their reasoning from there."
            ),
        )
