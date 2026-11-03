"""The pending-only logic of the nightly legacy sync, against an in-memory Firestore."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from app.migration import b2c_inventory, b2c_sync

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
OLD = NOW - timedelta(days=2)


class FakeFirestore:
    """Just enough of a Firestore client: collections of `{id: (update_time, fields)}`."""

    def __init__(self, collections: dict[str, dict[str, tuple[datetime, dict[str, Any]]]]) -> None:
        self.data = collections
        self.fetched: list[tuple[str, str]] = []

    def collections(self) -> list[Any]:
        return [SimpleNamespace(id=name) for name in self.data]

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self, name)

    def get_all(self, references: list[Any]) -> list[Any]:
        snapshots = []
        for reference in references:
            self.fetched.append((reference.collection, reference.doc_id))
            row = self.data[reference.collection].get(reference.doc_id)
            snapshots.append(
                SimpleNamespace(
                    id=reference.doc_id,
                    exists=row is not None,
                    update_time=row[0] if row else None,
                    to_dict=lambda row=row: dict(row[1]) if row else {},
                )
            )
        return snapshots


class FakeCollection:
    def __init__(self, owner: FakeFirestore, name: str) -> None:
        self.owner, self.name = owner, name

    def select(self, _fields: list[str]) -> FakeCollection:
        return self

    def stream(self) -> list[Any]:
        return [
            SimpleNamespace(id=doc_id, update_time=row[0])
            for doc_id, row in self.owner.data[self.name].items()
        ]

    def document(self, doc_id: str) -> Any:
        return SimpleNamespace(collection=self.name, doc_id=doc_id)


def test_only_new_and_changed_documents_are_pending() -> None:
    firestore = FakeFirestore(
        {
            "transcripts": {
                "already": (OLD, {}),
                "edited": (OLD, {}),
                "brand-new": (OLD, {}),
                "in-progress": (NOW - timedelta(minutes=5), {}),
            }
        }
    )
    ledger = {"transcripts": {"already": OLD, "edited": OLD - timedelta(days=1)}}
    pending, plans = b2c_sync.plan_pending(firestore, ledger, now=NOW)
    assert sorted(pending["transcripts"]) == ["brand-new", "edited"]
    [plan] = [plan for plan in plans if plan.collection == "transcripts"]
    assert (plan.in_firestore, plan.already_copied, plan.pending, plan.settling) == (4, 2, 2, 1)


def test_a_collection_the_old_site_does_not_have_yet_is_planned_empty() -> None:
    pending, _plans = b2c_sync.plan_pending(FakeFirestore({}), {}, now=NOW)
    assert pending["ortho_transcripts"] == {}


def test_the_client_fetches_only_pending_documents_and_remembers_them() -> None:
    firestore = FakeFirestore(
        {"transcripts": {"a": (OLD, {"n": 1}), "b": (OLD, {"n": 2}), "c": (OLD, {"n": 3})}}
    )
    client = b2c_sync.PendingClient(firestore, {"transcripts": {"b": OLD}})
    fetched = [snapshot.id for snapshot in client.collection("transcripts").stream()]
    assert fetched == ["b"]
    assert firestore.fetched == [("transcripts", "b")]
    assert client.take_served({"transcripts"}) == {("transcripts", "b"): OLD}
    assert client.take_served({"transcripts"}) == {}


def test_a_collection_outside_the_plan_is_refused_not_silently_empty() -> None:
    client = b2c_sync.PendingClient(FakeFirestore({}), {})
    with pytest.raises(RuntimeError, match="not in the sync plan"):
        list(client.collection("mystery").stream())


def test_a_late_feedback_pulls_in_its_already_copied_transcript() -> None:
    transcripts = b2c_inventory.TRANSCRIPT_COLLECTIONS["sca"]
    feedbacks = b2c_inventory.FEEDBACK_COLLECTIONS["sca"]
    transcript = {
        "_collection": transcripts,
        "id": "t1",
        "app_type": "sca",
        "attempt_id": "att-1",
        "user_id": "u1",
        "mock_id": "m",
        "station_id": "s",
    }
    unrelated = {
        "_collection": transcripts,
        "id": "t2",
        "app_type": "sca",
        "attempt_id": "att-2",
        "user_id": "u2",
        "mock_id": "m",
        "station_id": "s",
    }
    feedback = {
        "_collection": feedbacks,
        "id": "f1",
        "app_type": "sca",
        "attempt_id": "att-1",
        "user_id": "u1",
        "mock_id": "m",
        "station_id": "s",
    }
    other_feedback = {
        "_collection": feedbacks,
        "id": "f2",
        "app_type": "sca",
        "attempt_id": "att-2",
        "user_id": "u2",
        "mock_id": "m",
        "station_id": "s",
    }
    chosen = b2c_sync.attempt_inputs([feedback], [transcript, unrelated, feedback, other_feedback])
    assert [document["id"] for document in chosen] == ["t1", "f1"]


def test_steps_follow_their_pending_documents() -> None:
    plans = [
        b2c_sync.CollectionPlan("stations", 5, 4, 1, 0),
        b2c_sync.CollectionPlan("transcripts", 5, 5, 0, 0),
        b2c_sync.CollectionPlan("feedbacks", 5, 4, 1, 0),
    ]
    assert b2c_sync.steps_with_work(plans) == {"stations", "templates", "attempts", "mocks"}
