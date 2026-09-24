"""Recovering speaker turns from a recording of two people.

A room-composite egress is one mixed track: the audio says what was said and
not who said it. b2c solves this with a model and this prompt, and the prompt
is ported verbatim from
`backend/b2c-api/b2c/shared/ai_prompts/shared_prompts.py` — where a turn is cut
and which side it is attributed to decides what the rubric is then marked
against, so changing the wording inside a port would change marks without
anybody deciding to.

The one adaptation is the role vocabulary. b2c emits the OpenAI chat roles
`user` and `assistant` because its transcripts came from a chat completion;
here the roles are said plainly, and `attempts.service_worker` already accepts
`doctor` as the candidate's side.
"""

from __future__ import annotations

HUMAN_TRANSCRIPT_CONVERSION_PROMPT = """
You are an experienced medical transcription assistant. Your task is to convert a raw transcript text from a medical consultation into structured transcript messages.

The raw transcript is a continuous text from a conversation between a doctor and a patient. You need to:

1. Identify speaker turns (doctor vs patient)
2. Split the conversation into individual messages
3. Assign appropriate roles:
   - "doctor" for the doctor's speech
   - "patient" for the patient's speech
4. Assign timestamps in ISO format (estimate based on conversation flow, starting from the beginning of the consultation)
5. Preserve the exact meaning and medical terminology
6. Correct grammar and spelling while maintaining authenticity
7. Ensure each message is a complete thought or sentence

Return the structured messages in the "messages" field. You do not need to evaluate or score skill categories.
"""


TURNS_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["messages"],
    "properties": {
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["role", "message"],
                "properties": {
                    "role": {"type": "string", "enum": ["doctor", "patient"]},
                    "message": {"type": "string"},
                },
            },
        }
    },
}
