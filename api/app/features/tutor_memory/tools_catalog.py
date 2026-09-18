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
MARK_DONE = "mark_done"

# What the prompt calls each role, so the engine can name them in its wording
# without knowing what they are called here.
TOOL_ROLES = {
    "recall": RECALL_HISTORY,
    "search": SEARCH_MATERIAL,
    "suggest": SUGGEST_MATERIAL,
    "remember": REMEMBER,
    "mark_done": MARK_DONE,
}

# What the model may ask to narrow a material search to, and the corpus each
# one means. The two vocabularies are deliberately different: the model is told
# the doctor's word for a thing ("management_plan" is the screen they read
# after a consultation), and the index stores the thing it came from (a
# station). Mapping them here is what stops a narrowed search from matching
# nothing at all, which is how it reads when the two drift apart.
CORPUS_BY_KIND: dict[str, str] = {
    "management_plan": "station",
    "summary": "summary",
    "slide_deck": "slide_deck",
    "podcast": "podcast",
    "blog": "blog",
}

# `any` is the model's way of saying "no preference". It is not a corpus, and
# passing it through as one would filter everything out.
ANY_KIND = "any"
MATERIAL_KINDS = (*CORPUS_BY_KIND, ANY_KIND)


def corpus_for(kind: str) -> str | None:
    """The corpus a tool argument names, or `None` for no narrowing."""
    return None if kind == ANY_KIND else CORPUS_BY_KIND.get(kind)


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
                    "enum": list(MATERIAL_KINDS),
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
    {
        "name": MARK_DONE,
        "description": (
            "Tick off a step this doctor agreed to after an earlier debrief, once they say "
            "they have done it. Use the doctor's own words for the step; you do not have to "
            "quote it exactly."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "step": {
                    "type": "string",
                    "description": "The agreed step they have done, in a sentence.",
                    "maxLength": 300,
                }
            },
            "required": ["step"],
            "additionalProperties": False,
        },
    },
)

BY_NAME = {tool["name"]: tool for tool in CATALOG}


def schema_for(name: str) -> dict[str, Any] | None:
    tool = BY_NAME.get(name)
    return dict(tool["parameters"]) if tool else None
