"""The tools the tutor is given, as the worker will advertise them.

The worker holds no idea what any of these mean: it registers the schema, the
model calls it, and the arguments come back here. So this file is the whole
contract — the name the model sees, the sentence that tells it when to call,
and the JSON schema its arguments are checked against.

Kept apart from `service_tools.py`, which answers them, because the catalogue
is also what `service_session.py` puts on the bootstrap, and a list of tools
should be readable without reading how each is implemented.
"""

from __future__ import annotations

from typing import Any

RECALL_HISTORY = "recall_history"
SEARCH_MATERIAL = "search_material"
SUGGEST_MATERIAL = "suggest_material"
REMEMBER = "remember"

# What the prompt calls each role, so the engine can name them in its wording
# without knowing what they are called here.
TOOL_ROLES = {
    "recall": RECALL_HISTORY,
    "search": SEARCH_MATERIAL,
    "suggest": SUGGEST_MATERIAL,
    "remember": REMEMBER,
}

CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": RECALL_HISTORY,
        "description": (
            "Look up something from this doctor's own past: a consultation, a debrief, a note "
            "you made, or something they read or practised. Use it when they ask about "
            "something that is not already in your notes, or want more detail than the notes "
            "carry."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to look for, in the doctor's own words.",
                    "maxLength": 200,
                },
                "kind": {
                    "type": "string",
                    "description": "Narrow the search to one kind of memory.",
                    "enum": ["consultation", "debrief", "note", "activity", "any"],
                },
                "limit": {
                    "type": "integer",
                    "description": "How many to bring back.",
                    "minimum": 1,
                    "maximum": 5,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": SEARCH_MATERIAL,
        "description": (
            "Search the study material for an answer to a clinical question, and cite where "
            "it came from. Use it whenever they ask what to do for a condition."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The clinical question.",
                    "maxLength": 200,
                },
                "kind": {
                    "type": "string",
                    "description": "Narrow to one kind of material.",
                    "enum": ["management_plan", "summary", "slide_deck", "any"],
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": SUGGEST_MATERIAL,
        "description": (
            "Put something on the doctor's screen to open afterwards — a station to practise "
            "or a piece of reading. Say in one sentence why you chose it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "The identifier of the thing to suggest, as a lookup gave it to you.",
                    "maxLength": 120,
                },
                "reason": {
                    "type": "string",
                    "description": "Why this one, in one sentence, in your own words.",
                    "maxLength": 300,
                },
            },
            "required": ["ref", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": REMEMBER,
        "description": (
            "Write down one thing this doctor has told you that is worth having next time: "
            "when their exam is, what they find hard, what they want to work on."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "The one thing to remember, in a single sentence.",
                    "maxLength": 300,
                }
            },
            "required": ["fact"],
            "additionalProperties": False,
        },
    },
)

BY_NAME = {tool["name"]: tool for tool in CATALOG}


def schema_for(name: str) -> dict[str, Any] | None:
    tool = BY_NAME.get(name)
    return dict(tool["parameters"]) if tool else None
