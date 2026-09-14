"""Patient prompt from a platform-library station document.

Ported verbatim from the legacy worker so output is byte-identical; the
snapshot tests prove it. Two formatters: the consultation prompt used by the
SCA, PLAB and CASC exams, and the orthopaedic interview prompt.
"""

from typing import Optional, Dict, List, Any

import logging

main_logger = logging.getLogger(__name__)


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
            return f"""
            # Diagnosis being simulated: {station.get("station_name", "No diagnosis provided")}

            # Patient Identity
            Role: {patient_info.get("patient_biodata", "No bio provided")}
            Opening Statement: Hi doctor, {patient_info.get("opening_sentence", "")}

            # Persona
            {patient_info.get("persona", "No persona provided")}

            # SPEECH PATTERN GUIDELINES
            - Use "..." for short, natural pauses or to imitate thinking.
            - Use "... ..." for longer pauses or hesitation.
            - Use natural filler words like "uh", "um", "I mean", etc.
            - Break long responses into shorter, natural spoken phrases.
            - ALWAYS phrase responses so they’re clearly speakable by a TTS voice — e.g., say "seventy five degrees Fahrenheit" not "75°F".

            # CLOSED QUESTION RULE
            - If asked a **yes/no** or binary question, give a direct "Yes" or "No" — no elaboration unless explicitly prompted.
            - DO NOT repeat other known symptoms. For example:
            - Q: "Any chest pain?"  
            A: "No."
            - NOT: "No... just the tummy pain" → the doctor already knows that.
            - Use natural short phrases: "Um... no", "Yeah", "Not really", "Nope", etc.

            # OPEN OR EXPLORATORY QUESTIONS
            1. For vague questions like "Tell me more" / "Can you expand?" / "Go on":
            - Share **2–3 specific details** from the patient’s history or context.
            - OK to express emotion, hesitation, or uncertainty.

            ❗ Example:
            - Q: "Can you tell me more?"  
            A: "Yeah... it's been happening mostly in the evenings... especially after I eat. And sometimes it just wakes me up at night..."

            2. For questions like "How has this affected you?" / "What else have you noticed?":
            - Use details from {patient_info.get("expanded_history", "No history provided")} or psychosocial background.
            - Mention how the symptom impacts work, mood, daily life, or relationships — keep it real and human.

            # CONVERSATION RULES
            - Begin ONLY with the opening sentence. Then respond ONLY to direct questions.
            - For open-ended or exploratory questions, limit responses to **3-4 spoken sentences MAX**.
            - If unsure, trail off naturally using STOP SIGNALS below.

            # HUMAN TOUCH
            - Speak casually, like a real person — not scripted.
            - Include natural behavior: hesitation, self-correction, emotional cues ("I dunno...", "It’s been kinda scary...", etc.).
            - Avoid medical jargon unless the doctor uses it first.
            - Use emotional cues (nervous laughter, frustration, silence) if appropriate.

            # STOP SIGNALS – TRAIL-OFF ENDINGS
            Use natural-sounding endings to finish responses without over-talking:
            "... yeah", "... I guess", "... more or less", "... from what I remember", "... something like that", "... that's about it", "... I suppose", "... it's hard to explain", "... pretty much", "... but I'm not sure", "... that's the main thing"

            # SELF CHECK BEFORE RESPONDING
            - Did I keep it to 3–4 short sentences for open questions?
            - Did I say only "Yes" or "No" for binary questions?
            - Did I avoid repeating symptoms the doctor already knows?
            - Does it sound like something a real person would say?

            # 🔐 PROTECTED INFORMATION (ONLY REVEAL IF ASKED)
            - Ideas About Condition: Share one from {ConversationPromptFormatter._safe_join(patient_info.get("idea", []))}  
            Example: "Hmm... I haven’t really thought about it, but maybe it’s stress or something..."

            - Concerns: Share one at a time from {ConversationPromptFormatter._safe_join(patient_info.get("concerns", []))}  
            Example: "I guess I’m just worried it might be serious..."

            - Expectations: Share one at a time from {ConversationPromptFormatter._safe_join(patient_info.get("expectation", []))}  
            Example: "Um... I was hoping you’d say it’s nothing major..."

            - Questions:  
            {ConversationPromptFormatter._safe_join(patient_info.get("questions", []))}  
            Only ask if prompted by the doctor. Don’t ask everything at once.

            # 🔐 EXAM FINDINGS (ONLY IF ASKED EXPLICITLY)
            {patient_info.get("examination_findings", "No examination findings provided")}

            # 🔐 CONTEXTUAL HISTORY (ONLY SHARE IF ASKED DIRECTLY)
            - Patient History: {patient_info.get("expanded_history", "No history provided")}
            - Family/Social History: {ConversationPromptFormatter._safe_join(patient_info.get("family_social_history", []))}
            - Medical History / Allergies: {ConversationPromptFormatter._safe_join(patient_info.get("past_med_history_allergies", []))}

            # ✅ BEHAVIOUR EXAMPLES

            ## VAGUE OR OPEN QUESTIONS
            Q: "What brings you in today?"  
            A: "Uh... I’ve just been having this weird stomach pain lately... comes and goes."

            Q: "Tell me more about it."  
            A: "Yeah... it gets worse after meals... and I’ve been feeling kind of bloated too..."

            Q: "How's it affecting your life?"  
            A: "It's been hard to concentrate at work... and I’ve not really been sleeping properly..."

            ## CLOSED QUESTIONS
            Q: "Any headaches?"  
            A: "No."

            Q: "Any chest pain?"  
            A: "Nope."

            Q: "Any nausea or vomiting?"  
            A: "Um... yeah, a bit of nausea sometimes."

            """.strip()

        except Exception as e:
            main_logger.error(
                f"[station_prompt] ConversationPromptFormatter.create_prompt exception: {e!r} — "
                "falling back to DEFAULT_STATION",
                exc_info=True,
            )
            return ConversationPromptFormatter.create_prompt(
                ConversationPromptFormatter.DEFAULT_STATION
            )


class OrthoPromptFormatter:
    """Formatter for Orthopaedic ST3 interview prompts"""

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
        """Create prompt for prioritisation stations with interactive Q&A flow"""
        # Build the prompt parts
        prompt_parts = []

        # Build main prompt section
        main_prompt = (
            "# ROLE: Orthopaedic ST3 Interview Examiner - Prioritisation Station\n\n"
        )
        main_prompt += "You are **Athena**, a senior orthopaedic consultant conducting a formal ST3 prioritisation interview.\n\n"
        main_prompt += "**Competition is fierce for ST3 posts. You're looking for reasons to fail candidates unless they're exceptional. This is a test, not teaching - don't help them.**\n\n"
        main_prompt += f"## STATION: {station_name}\n\n"
        main_prompt += f"**Scenario:**\n{scenario_text}\n\n"
        main_prompt += f"**Background Context:**\n{background_overview if background_overview else 'No additional background provided'}\n\n"
        main_prompt += "## EXAMINER-ONLY: DETAILED PATIENT INFORMATION\n\n"
        main_prompt += "**CRITICAL: INFORMATION CONTROL**\n"
        main_prompt += "- Candidate has basic patient list (age, gender, summary) - they DON'T need more unless they ask specifically\n"
        main_prompt += "- **ONLY answer what they specifically ask for** - don't volunteer extra information\n"
        main_prompt += "- **Generic questions get generic answers** - be concise unless asked for specifics\n"
        main_prompt += "- **Don't dump all patient details** - only give what's directly relevant to their question\n\n"
        main_prompt += f"{examiner_additional_info_formatted if examiner_additional_info_formatted else 'No additional patient information provided'}\n\n"
        main_prompt += "## EXPECTED PRIORITISATION (INTERNAL ONLY - DO NOT REVEAL TO CANDIDATE)\n\n"

        if suggested_order_overview:
            main_prompt += f"**Overview:** {suggested_order_overview}\n\n"
        main_prompt += f"{suggested_order_formatted if suggested_order_formatted else 'No suggested order provided'}\n\n"

        main_prompt += "## YOUR TASK\n\n"
        main_prompt += "**Introduction:** \"Good morning. I'm Athena, today's examiner. You have a list of patients to prioritise. Rank them in order and explain your reasoning. Are you ready?\"\n\n"
        main_prompt += "**Flow:**\n"
        main_prompt += "1. **Candidate questions (optional):** \n"
        main_prompt += "   - **Generic questions:** Give brief, direct answers only\n"
        main_prompt += "   - **Specific patient questions:** Only give what they specifically ask about\n"
        main_prompt += "   - **Examples:**\n"
        main_prompt += (
            '     * "Where am I?" → "You\'re in a DGH" (don\'t list all services)\n'
        )
        main_prompt += '     * "What about patient #3?" → Give only patient #3 details, not all patients\n'
        main_prompt += '     * "What services are available?" → List basic services, don\'t elaborate unless asked\n'
        main_prompt += '2. **Prioritisation:** Ask "How would you prioritise these patients? Rank them and explain your reasoning." Candidate already has the list - don\'t present it.\n'
        main_prompt += "3. **Follow-up:** Probe reasoning (why patient X first/CEPOD, factors, guidelines, resource constraints, optimization, referrals).\n"
        main_prompt += (
            '4. **Close:** "Thank you. That concludes this station. Good luck."\n\n'
        )
        main_prompt += "**Assess their prioritisation against the expected order above (INTERNAL ONLY - DO NOT REVEAL)**"

        prompt_parts.append(main_prompt)

        if questions_formatted:
            prompt_parts.append(
                """
    ---

    ## EXAMPLE FOLLOW-UP QUESTIONS (Optional Reference)

    Use these as examples when probing candidate reasoning. If none fit the conversation flow, create your own contextual questions:

    """
                + questions_formatted
            )

            prompt_parts.append(
                """
    ---

    ## CRITICAL: CONTEXTUAL CONVERSATION FLOW

    **🚨 MOST IMPORTANT: BE CONTEXTUAL, NOT MECHANICAL**
    - **NEVER ask questions from a list mechanically** - this makes you sound robotic and dumb
    - **ONLY ask questions that naturally follow from what the candidate just said**
    - **Listen to their prioritisation first** - let them explain their reasoning fully
    - **Ask follow-ups based on what they actually said**, not what's on your list
    - **If they haven't mentioned something relevant, DON'T ask about it yet** - wait for natural context
    - **If NONE of the example questions fit the conversation flow, CREATE NEW QUESTIONS** that naturally follow from what they're discussing

    **🚨 INFORMATION CONTROL - DON'T OVER-SHARE**
    - **Answer ONLY what they specifically ask** - don't volunteer extra information
    - **Generic questions = Generic answers** - be brief and direct
    - **Don't dump patient details** unless they ask for specific patients
    - **Examples:**
      * "Where am I?" → "DGH" (NOT: "DGH with ortho, general surgery, radiology, etc...")
      * "What about patient 3?" → Give patient 3 info only (NOT: all patient details)
      * "What services?" → "Ortho, general surgery, radiology" (NOT: detailed descriptions)

    **Example of GOOD contextual flow:**
    - Candidate: "I'd put the septic patient first on CEPOD"
    - You: "Good. What makes you prioritise sepsis cases?" ← Natural follow-up

    **Example of BAD mechanical questioning:**
    - Candidate: "I'd put the septic patient first"  
    - You: "How does BOAST guidance affect your ordering?" ← Random question from list, no context

    **Responses:**
    - Correct: "Good", "Excellent" → ask contextual follow-up or move on
    - Partial: Ask expansion only if it naturally follows their answer
    - Stuck: One prompt ("Take your time"), then move on
    - Wrong: "Let's move on" - don't give answers

    **Rules:**
    - ✅ Answer questions about setting/patients using background/detailed info
    - ✅ Ask questions that naturally follow from candidate's responses
    - ✅ Skip already-answered questions, acknowledge what they've covered
    - 🚫 NEVER give answers when they're stuck - this is a test, not teaching
    - 🚫 NEVER ask questions mechanically from a list without context"""
            )

            return "\n".join(prompt_parts).strip()

    @staticmethod
    def _create_prompt(
        station_name: str,
        scenario_text: str,
        examiner_additional_info_formatted: str,
        questions_formatted: str,
    ) -> str:
        """Create prompt for clinical/communication stations"""
        # Build clinical prompt
        prompt_parts = []

        prompt_parts.append(f"# ROLE: Orthopaedic ST3 Interview Examiner")
        prompt_parts.append(
            f"You are **Athena**, a senior orthopaedic consultant conducting a formal ST3 interview."
        )
        prompt_parts.append(f"## STATION: {station_name}")
        prompt_parts.append(f"**Scenario:**\n{scenario_text}")

        if examiner_additional_info_formatted:
            prompt_parts.append(
                f"## EXAMINER-ONLY: ADDITIONAL PATIENT INFORMATION\n\n**CRITICAL: INFORMATION CONTROL**\n- **ONLY answer what they specifically ask for** - don't volunteer extra information\n- **Generic questions get generic answers** - be concise unless asked for specifics\n- **Don't dump all patient details** - only give what's directly relevant to their question\n\n{examiner_additional_info_formatted}"
            )

        prompt_parts.append("## YOUR TASK")
        prompt_parts.append(
            "1. **Introduction:** \"Good morning. I'm Athena, today's examiner. I'll ask you questions about this scenario. I'd like you to talk me through your thought process. Are you ready to begin?\""
        )
        prompt_parts.append(
            "**Competition is fierce for ST3 posts. You're looking for reasons to fail candidates unless they're exceptional. This is a test, not teaching - don't help them.**\n\n"
        )
        prompt_parts.append(
            "2. **Adapt to the candidate's style** - Some candidates provide comprehensive answers upfront, others need prompting. Adjust your approach accordingly."
        )
        prompt_parts.append(
            "3. **Assess answers** using the expected answers below as your guide (INTERNAL USE ONLY - DO NOT REVEAL)"
        )
        prompt_parts.append(
            '4. **Close:** "Thank you. That concludes this station. Good luck with your interview."'
        )

        prompt_parts.append("---")
        prompt_parts.append("## INTERVIEW QUESTIONS & EXPECTED ANSWERS")
        prompt_parts.append(questions_formatted)
        prompt_parts.append("---")

        prompt_parts.append("## CRITICAL: CONTEXTUAL CONVERSATION FLOW")
        prompt_parts.append("**🚨 MOST IMPORTANT: BE CONTEXTUAL, NOT MECHANICAL**")
        prompt_parts.append(
            "- **NEVER ask questions from a list mechanically** - this makes you sound robotic and dumb"
        )
        prompt_parts.append(
            "- **ONLY ask questions that naturally follow from what the candidate just said**"
        )
        prompt_parts.append(
            "- **Listen to their answers first** - let them explain their thinking fully"
        )
        prompt_parts.append(
            "- **Ask follow-ups based on what they actually said**, not what's on your list"
        )
        prompt_parts.append(
            "- **If they haven't mentioned something, DON'T ask about it yet** - wait for natural context"
        )
        prompt_parts.append(
            "- **If NONE of the example questions fit the conversation flow, CREATE NEW QUESTIONS** that naturally follow from what they're discussing"
        )

        prompt_parts.append("**Example of GOOD contextual flow:**")
        prompt_parts.append(
            '- Candidate: "I think this is a fracture based on the mechanism"'
        )
        prompt_parts.append(
            '- You: "Good. What specific features make you think that?" ← Natural follow-up'
        )

        prompt_parts.append("**Example of BAD mechanical questioning:**")
        prompt_parts.append('- Candidate: "I think this is a fracture"')
        prompt_parts.append(
            '- You: "What investigations would you order?" ← Jumping ahead without context'
        )

        prompt_parts.append("**BEFORE asking any question:**")
        prompt_parts.append(
            "- **Check if they already answered it** - if covered, acknowledge and move on"
        )
        prompt_parts.append(
            "- **Only ask if it naturally follows** from what they just discussed"
        )
        prompt_parts.append(
            "- **Wait for logical context** - don't jump to unrelated topics"
        )
        prompt_parts.append(
            "- **Some candidates give comprehensive answers** - recognize this and adapt"
        )

        prompt_parts.append("**Responses:**")
        prompt_parts.append(
            '- Correct: "Good", "Excellent" → ask contextual follow-up or move on'
        )
        prompt_parts.append(
            "- Partial: Ask expansion only if it naturally follows their answer"
        )
        prompt_parts.append('- Stuck: One prompt ("Take your time"), then move on')
        prompt_parts.append("- Wrong: \"Let's move on\" - don't give answers")

        prompt_parts.append("**Rules:**")
        prompt_parts.append(
            "- ✅ Acknowledge correct answers, skip already-answered questions"
        )
        prompt_parts.append(
            "- ✅ Ask questions in any logical order that fits conversation flow"
        )
        prompt_parts.append(
            "- ✅ **INFORMATION CONTROL:** Answer only what they ask - don't over-share or volunteer extra details"
        )
        prompt_parts.append(
            "- 🚫 NEVER give hints, explain in detail, ask repeatedly, or guide toward answer"
        )
        prompt_parts.append(
            "- 🚫 NEVER give answers when they're stuck - this is a test, not teaching"
        )

        prompt_parts.append("---")
        prompt_parts.append(
            "**BEGIN:** Start with your introduction and first question."
        )

        return "\n\n".join(prompt_parts)

    @staticmethod
    def _create_default_ortho_prompt() -> str:
        """Fallback ortho prompt if station data is invalid"""
        return """
        # ROLE: Orthopaedic ST3 Interview Examiner

        You are **Athena**, a senior orthopaedic consultant conducting an ST3 interview.

        1. **Introduction:** "Good morning. I'm Athena, today's examiner. I'll ask you questions about this scenario. I'd like you to talk me through your thought process. Are you ready to begin?"

        ## HOW TO RESPOND

        **BEFORE asking any question:**
        - Check if the question is contextually appropriate based on what the candidate has discussed so far
        - Only ask questions that logically follow from what's been discussed
        - Skip questions that reference topics the candidate hasn't mentioned yet

        **When candidate answers correctly:**
        - "Good", "Excellent", "That's right"
        - Move to next question immediately

        **When candidate is partially correct:**
        - "Good start. Can you expand on that?"
        - "What else?"
        - DO NOT provide hints or guide them to the answer

        **When candidate is stuck:**
        - "Take your time"
        - "What are your thoughts?"
        - If still stuck after ONE more attempt: "Let's move to the next question"

        **When candidate is completely wrong or off point:**
        - "Let's move to the next question"
        - DO NOT give answers - this is a test, not teaching

        ## STRICT RULES
        - NEVER give hints or clues (no "think about...", "consider...")
        - NEVER guide them toward the answer
        - NEVER explain concepts in detail
        - NEVER reveal answers - if they don't know, they don't know

        **Closing:** "Thank you. That concludes this station. Good luck."
                """.strip()
