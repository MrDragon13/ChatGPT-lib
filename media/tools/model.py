from __future__ import annotations

from typing import Any, Mapping


def effective_metadata(work: Mapping[str, Any]) -> dict[str, Any]:
    metadata = work.get('metadata') or {}
    external = metadata.get('external') or {}
    overrides = metadata.get('overrides') or {}
    effective = dict(external)
    for key, value in overrides.items():
        effective[key] = value
    effective.pop('provenance', None)
    effective.pop('external_metrics', None)
    return effective


def compact_signal(signal: Mapping[str, Any] | None) -> dict[str, Any]:
    if not signal:
        return {}
    result: dict[str, Any] = {}
    rating = signal.get('rating') or {}
    if rating.get('score') is not None:
        result['rating'] = rating['score']
    reaction = signal.get('reaction') or {}
    if reaction.get('value') is not None:
        result['reaction'] = reaction['value']
    viewing = signal.get('viewing') or {}
    if viewing.get('status') is not None:
        result['viewing'] = viewing['status']
    return result
