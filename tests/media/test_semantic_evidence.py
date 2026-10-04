from __future__ import annotations

from media.service.semantic_evidence import classify_candidate_traits


def _affinity(
    score: float,
    *,
    confidence: str = "medium",
    evidence_count: int = 2,
) -> dict[str, object]:
    return {
        "score": score,
        "confidence": confidence,
        "evidence_count": evidence_count,
    }


def test_classifies_positive_and_negative_affinities_with_details():
    result = classify_candidate_traits(
        ["story.intrigue", "humor.absurd"],
        {
            "story.intrigue": _affinity(0.75, confidence="high", evidence_count=4),
            "humor.absurd": _affinity(-0.4, confidence="low", evidence_count=1),
        },
    )

    assert result["fingerprint_trait_count"] == 2
    assert result["strengths"] == ["story.intrigue"]
    assert result["concerns"] == ["humor.absurd"]
    assert result["evidence_details"] == {
        "strengths": [
            {
                "term": "story.intrigue",
                "direction": "positive",
                "affinity_score": 0.75,
                "confidence": "high",
                "evidence_count": 4,
            }
        ],
        "concerns": [
            {
                "term": "humor.absurd",
                "direction": "negative",
                "affinity_score": -0.4,
                "confidence": "low",
                "evidence_count": 1,
            }
        ],
    }
    assert result["strengths_count"] == 1
    assert result["concerns_count"] == 1
    assert result["net_directional_count"] == 0
    assert result["directional_match_count"] == 2
    assert result["ranking_basis"] == "trait_overlap"
    assert result["fallback_reason"] is None


def test_zero_and_missing_affinities_are_unmatched():
    result = classify_candidate_traits(
        ["story.intrigue", "visual.atmosphere"],
        {"story.intrigue": _affinity(0.0)},
    )

    assert result["strengths"] == []
    assert result["concerns"] == []
    assert result["directional_match_count"] == 0
    assert result["net_directional_count"] == 0
    assert result["ranking_basis"] == "none"
    assert result["fallback_reason"] == "no_matching_affinities"


def test_empty_fingerprint_has_explicit_fallback_reason():
    result = classify_candidate_traits([], {"story.intrigue": _affinity(1.0)})

    assert result["fingerprint_trait_count"] == 0
    assert result["strengths"] == []
    assert result["concerns"] == []
    assert result["ranking_basis"] == "none"
    assert result["fallback_reason"] == "no_semantic_fingerprint"


def test_fingerprint_without_known_affinity_is_not_personalized():
    result = classify_candidate_traits(
        ["story.intrigue"],
        {"visual.atmosphere": _affinity(0.5)},
    )

    assert result["fingerprint_trait_count"] == 1
    assert result["directional_match_count"] == 0
    assert result["ranking_basis"] == "none"
    assert result["fallback_reason"] == "no_matching_affinities"


def test_confidence_is_passthrough_and_does_not_threshold_direction():
    result = classify_candidate_traits(
        ["story.intrigue", "humor.absurd"],
        {
            "story.intrigue": _affinity(0.01, confidence="low", evidence_count=1),
            "humor.absurd": _affinity(-0.01, confidence="low", evidence_count=1),
        },
    )

    assert result["strengths"] == ["story.intrigue"]
    assert result["concerns"] == ["humor.absurd"]
    assert result["evidence_details"]["strengths"][0]["confidence"] == "low"
    assert result["evidence_details"]["concerns"][0]["confidence"] == "low"


def test_duplicate_traits_are_counted_once_in_fingerprint_and_evidence():
    result = classify_candidate_traits(
        ["story.intrigue", "story.intrigue", "humor.absurd"],
        {
            "story.intrigue": _affinity(0.8),
            "humor.absurd": _affinity(-0.2),
        },
    )

    assert result["fingerprint_trait_count"] == 2
    assert result["strengths"] == ["story.intrigue"]
    assert result["concerns"] == ["humor.absurd"]
    assert result["directional_match_count"] == 2


def test_rich_fingerprint_count_is_retained_without_normalization():
    traits = [f"term.{index}" for index in range(8)]
    result = classify_candidate_traits(
        traits,
        {
            "term.0": _affinity(0.5),
            "term.1": _affinity(-0.25),
        },
    )

    assert result["fingerprint_trait_count"] == 8
    assert result["strengths_count"] == 1
    assert result["concerns_count"] == 1
    assert result["net_directional_count"] == 0
    assert result["directional_match_count"] == 2
