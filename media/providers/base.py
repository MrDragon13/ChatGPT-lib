from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol


@dataclass(frozen=True)
class ProviderCandidate:
    media_type: Literal["movie", "tv"]
    provider_id: int
    title: str
    original_title: str
    year: int | None


@dataclass(frozen=True)
class CanonicalMetadata:
    identity: Mapping[str, Any]
    external: Mapping[str, Any]


class MetadataProvider(Protocol):
    def search_work(self, title: str, year: int | None = None) -> list[ProviderCandidate]: ...
    def fetch_work(self, media_type: Literal["movie", "tv"], provider_id: int) -> CanonicalMetadata: ...
