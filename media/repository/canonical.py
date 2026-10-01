from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol


@dataclass(frozen=True)
class WorkRecord:
    path: Path
    data: Mapping[str, Any]

    @property
    def id(self) -> str:
        return str(self.data["id"])


class CanonicalRepository(Protocol):
    def get_work(self, work_id: str) -> WorkRecord | None: ...
    def iter_works(self) -> Iterator[WorkRecord]: ...
    def configured_targets(self) -> tuple[set[str], dict[str, list[str]]]: ...
