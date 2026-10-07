from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


@dataclass(frozen=True)
class WorkRef:
    id: str | None = None
    title: str | None = None
    year: int | None = None
    tmdb_media_type: Literal["movie", "tv"] | None = None
    tmdb_id: int | None = None
    imdb_id: str | None = None


@dataclass(frozen=True)
class TargetUpdate:
    target: str
    viewing: Mapping[str, Any] | None = None
    rating: Mapping[str, Any] | None = None
    reaction: Mapping[str, Any] | None = None
    feedback: Mapping[str, Any] | None = None


FeedbackComponent = Literal["viewing", "rating", "reaction", "feedback"]


@dataclass(frozen=True)
class TargetEdit:
    target: str
    set_values: Mapping[str, Any]
    clear: tuple[FeedbackComponent, ...] = ()
    purge: bool = False


@dataclass(frozen=True)
class ProviderIdentity:
    media_type: Literal["movie", "tv"]
    id: int


@dataclass(frozen=True)
class CreationContext:
    resolved_identity: Mapping[str, Any]
    provider_identity: ProviderIdentity
    minimum_metadata: Mapping[str, Any]


@dataclass(frozen=True)
class SemanticSnapshot:
    traits: tuple[Mapping[str, Any], ...]
    semantic_input_digest: str
    vocabulary_digest: str
    algorithm_version: str


@dataclass(frozen=True)
class MediaEntryPreconditions:
    expected_viewer_digests: Mapping[str, str]
