"""The tool loop against a scripted model: what it runs, what it tells the model, and when it stops."""

from __future__ import annotations

import json
from typing import Any

from app.features.media_production.agent_loop import (
    Limits,
    Reply,
    Tool,
    ToolCall,
    ToolOutput,
    run,
)


def call(name: str, **arguments: Any) -> Reply:
    return Reply(
        text="", calls=(ToolCall(id=f"call-{name}", name=name, arguments=json.dumps(arguments)),), tokens=10
    )


class Model:
    """Answers each turn with the next scripted reply, keeping what it was sent."""

    def __init__(self, *replies: Reply) -> None:
        self.replies = list(replies)
        self.seen: list[list[dict[str, Any]]] = []

    async def __call__(self, messages: list[dict[str, Any]], specs: list[dict[str, Any]]) -> Reply:
        self.seen.append([dict(message) for message in messages])
        return self.replies.pop(0) if self.replies else call("note", text="again")


def tools(notes: list[str]) -> list[Tool]:
    async def note(arguments: dict[str, Any]) -> ToolOutput:
        notes.append(arguments["text"])
        return ToolOutput(text=f"noted {arguments['text']}")

    async def broken(arguments: dict[str, Any]) -> ToolOutput:
        raise RuntimeError("the library is down")

    async def finish(arguments: dict[str, Any]) -> ToolOutput:
        return ToolOutput(text="finished", done=True)

    schema = {"type": "object", "properties": {"text": {"type": "string"}}}
    return [
        Tool("note", "Keeps a note.", schema, note),
        Tool("broken", "Always fails.", schema, broken),
        Tool("finish", "Ends the work.", schema, finish),
    ]


async def go_on(tool: str, text: str, tokens: int) -> bool:
    return True


async def started(model: Model, notes: list[str], limits: Limits | None = None, on_step: Any = go_on) -> Any:
    return await run(
        model, system="S", opening="O", tools=tools(notes), limits=limits or Limits(), on_step=on_step
    )


async def test_it_runs_the_tools_the_model_calls_and_ends_when_one_says_done() -> None:
    notes: list[str] = []
    model = Model(call("note", text="first"), call("note", text="second"), call("finish"))

    result = await started(model, notes)

    assert notes == ["first", "second"]
    assert (result.ended, result.turns, result.tokens) == ("finished", 3, 30)
    assert model.seen[0] == [{"role": "system", "content": "S"}, {"role": "user", "content": "O"}]
    assert model.seen[1][-1] == {"role": "tool", "tool_call_id": "call-note", "content": "noted first"}


async def test_a_tool_that_fails_or_does_not_exist_is_told_to_the_model_and_the_run_goes_on() -> None:
    bad_arguments = Reply(text="", calls=(ToolCall(id="c3", name="note", arguments="{not json"),), tokens=1)
    model = Model(call("broken"), call("missing"), bad_arguments, call("finish"))

    result = await started(model, [])

    assert result.ended == "finished"
    assert model.seen[1][-1]["content"] == "broken failed: the library is down"
    assert model.seen[2][-1]["content"] == "There is no tool called missing."
    assert model.seen[3][-1]["content"] == "note was not run: its arguments were not a JSON object."


async def test_it_stops_at_its_limits() -> None:
    assert (await started(Model(), [], Limits(turns=4))).ended == "turns"
    assert (await started(Model(), [], Limits(tokens=25))).ended == "tokens"
    assert (await started(Model(), [], Limits(seconds=-1))).ended == "time"


async def test_a_model_that_stops_calling_tools_is_asked_once_and_then_the_run_ends() -> None:
    words = Reply(text="I think I am done.", calls=(), tokens=5)
    model = Model(words, words)

    result = await started(model, [])

    assert result.ended == "silent"
    assert model.seen[1][-1] == {
        "role": "user",
        "content": "Call a tool to answer.",
    }


async def test_the_run_ends_when_the_step_says_stop() -> None:
    notes: list[str] = []
    steps: list[tuple[str, str, int]] = []

    async def stop_after_one(tool: str, text: str, tokens: int) -> bool:
        steps.append((tool, text, tokens))
        return False

    result = await started(
        Model(call("note", text="first"), call("note", text="second")), notes, on_step=stop_after_one
    )

    assert result.ended == "stopped"
    assert notes == ["first"]
    assert steps == [("note", "noted first", 10)]


async def test_pictures_shown_follow_the_opening_as_a_message() -> None:
    model = Model(call("finish"))

    await run(
        model,
        system="S",
        opening="O",
        tools=tools([]),
        limits=Limits(),
        on_step=go_on,
        shown=(b"jpeg-bytes",),
    )

    assert model.seen[0][2] == {
        "role": "user",
        "content": [
            {"type": "text", "text": "The pictures named above, in order."},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,anBlZy1ieXRlcw=="}},
        ],
    }
