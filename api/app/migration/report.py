"""What a load run did, in enough detail to compare against the export."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoadReport:
    users_created: int = 0
    users_matched: int = 0
    entitlements_created: int = 0
    entitlements_existing: int = 0
    attempts_created: int = 0
    attempts_existing: int = 0
    messages_created: int = 0
    results_created: int = 0
    stations_created: int = 0
    stations_existing: int = 0
    # A record that could not be loaded, and why. Collected rather than raised:
    # one unusable row should not abandon the other ten thousand, and skipping
    # somebody quietly is worse than either.
    problems: list[str] = field(default_factory=list)

    def problem(self, message: str) -> None:
        self.problems.append(message)

    @property
    def ok(self) -> bool:
        return not self.problems

    def merge(self, other: LoadReport) -> LoadReport:
        return LoadReport(
            users_created=self.users_created + other.users_created,
            users_matched=self.users_matched + other.users_matched,
            entitlements_created=self.entitlements_created + other.entitlements_created,
            entitlements_existing=self.entitlements_existing + other.entitlements_existing,
            attempts_created=self.attempts_created + other.attempts_created,
            attempts_existing=self.attempts_existing + other.attempts_existing,
            messages_created=self.messages_created + other.messages_created,
            results_created=self.results_created + other.results_created,
            stations_created=self.stations_created + other.stations_created,
            stations_existing=self.stations_existing + other.stations_existing,
            problems=[*self.problems, *other.problems],
        )

    def summary(self) -> str:
        return (
            f"users {self.users_created} created / {self.users_matched} matched; "
            f"entitlements {self.entitlements_created} created / "
            f"{self.entitlements_existing} already there; "
            f"attempts {self.attempts_created} created / {self.attempts_existing} already there; "
            f"messages {self.messages_created}; results {self.results_created}; "
            f"stations {self.stations_created} created / {self.stations_existing} already there; "
            f"problems {len(self.problems)}"
        )
