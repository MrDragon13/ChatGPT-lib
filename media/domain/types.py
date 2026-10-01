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
