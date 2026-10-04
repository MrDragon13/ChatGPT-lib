from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _unique_terms(traits: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for trait in traits:
        if not isinstance(trait, str) or not trait or trait in seen:
            continue
        seen.add(trait)
        result.append(trait)
    return result


def _detail(term: str, affinity: Mapping[str, Any], *, direction: str) -> dict[str, Any]:
    return {
        "term": term,
        "direction": direction,
        "affinity_score": affinity.get("score"),
        "confidence": affinity.get("confidence"),
        "evidence_count": affinity.get("evidence_count"),
    }


def classify_candidate_traits(
    traits: Iterable[str],
    affinities: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify candidate traits against signed target affinities.

    This is a pure observability/ranking primitive. Confidence and evidence
    metadata are passed through for explanation but do not threshold direction.
    """

    terms = _unique_terms(traits)
    strengths: list[str] = []
    concerns: list[str] = []
    strength_details: list[dict[str, Any]] = []
    concern_details: list[dict[str, Any]] = []

    for term in terms:
        affinity = affinities.get(term)
        if not isinstance(affinity, Mapping):
            continue
        score = affinity.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            continue
        if score > 0:
            strengths.append(term)
            strength_details.append(_detail(term, affinity, direction="positive"))
        elif score < 0:
            concerns.append(term)
            concern_details.append(_detail(term, affinity, direction="negative"))

    strengths_count = len(strengths)
    concerns_count = len(concerns)
    directional_match_count = strengths_count + concerns_count

    if not terms:
        ranking_basis = "none"
        fallback_reason = "no_semantic_fingerprint"
    elif directional_match_count == 0:
        ranking_basis = "none"
        fallback_reason = "no_matching_affinities"
    else:
        ranking_basis = "trait_overlap"
        fallback_reason = None

    return {
        "fingerprint_trait_count": len(terms),
        "strengths": strengths,
        "concerns": concerns,
        "evidence_details": {
            "strengths": strength_details,
            "concerns": concern_details,
        },
        "strengths_count": strengths_count,
        "concerns_count": concerns_count,
        "net_directional_count": strengths_count - concerns_count,
        "directional_match_count": directional_match_count,
        "ranking_basis": ranking_basis,
        "fallback_reason": fallback_reason,
    }
