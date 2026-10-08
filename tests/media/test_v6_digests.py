from copy import deepcopy

from media.domain.digests import (
    compute_semantic_input_digest,
    compute_viewer_digest,
    compute_vocabulary_digest,
    is_material_evidence_change,
    material_evidence_projection,
)
from media.domain.freshness import evaluate_metadata_freshness


def work_document():
    return {
        "schema_version": 4,
        "id": "arrival-2016",
        "entity_type": "work",
        "identity": {
            "format": "movie",
            "title_original": "Arrival",
            "title_ru": "Прибытие",
            "year": 2016,
            "external_ids": {"tmdb": {"media_type": "movie", "id": 329865}},
        },
        "metadata": {
            "external": {
                "genres": ["genre.science_fiction", "genre.drama"],
                "runtime_min": 116,
                "original_language": "en",
                "synopsis_short": "A linguist works to understand alien visitors.",
                "external_metrics": {
                    "tmdb": {"score": 7.6, "votes": 19000, "observed_at": "2026-10-01"}
                },
                "provenance": {
                    "provider": "tmdb",
                    "provider_id": 329865,
                    "fetched_at": "2026-10-01T00:00:00Z",
                },
            },
            "semantic": {
                "traits": [
                    {"term": "story.intrigue", "source": "llm_inferred", "confidence": "high"}
                ]
            },
        },
        "viewer_signals": {
            "primary": {
                "viewing": {"status": "watched"},
                "rating": {"score": 9, "source": "explicit", "confidence": "exact"},
                "reaction": {"value": "liked", "source": "explicit", "confidence": "high"},
                "feedback": {
                    "summary": "Очень понравилась загадка.",
                    "signals": [
                        {
                            "term": "story.intrigue",
                            "sentiment": "positive",
                            "strength": 3,
                            "source": "explicit",
                            "confidence": "high",
                        }
                    ],
                },
            }
        },
    }


def test_viewer_digest_ignores_unrelated_metadata_changes():
    before = work_document()
    after = deepcopy(before)
    after["metadata"]["external"]["runtime_min"] = 117
    after["metadata"]["external"]["external_metrics"]["tmdb"]["votes"] += 1

    assert compute_viewer_digest(before, "primary") == compute_viewer_digest(after, "primary")


def test_semantic_input_digest_ignores_dynamic_metrics_but_tracks_static_facts():
    work = work_document()
    dynamic_only = deepcopy(work)
    dynamic_only["metadata"]["external"]["external_metrics"]["tmdb"] = {
        "score": 8.0,
        "votes": 20000,
        "observed_at": "2026-10-07",
    }
    dynamic_only["metadata"]["external"]["provenance"]["fetched_at"] = "2026-10-07T00:00:00Z"

    static_change = deepcopy(work)
    static_change["metadata"]["external"]["runtime_min"] = 117

    vocab_digest = "sha256:" + "a" * 64
    baseline = compute_semantic_input_digest(work, vocab_digest, "media-semantic-v1")

    assert baseline == compute_semantic_input_digest(dynamic_only, vocab_digest, "media-semantic-v1")
    assert baseline != compute_semantic_input_digest(static_change, vocab_digest, "media-semantic-v1")


def test_material_evidence_ignores_summary_only_edit_but_tracks_structured_signal_change():
    before = work_document()["viewer_signals"]["primary"]
    typo_fix = deepcopy(before)
    typo_fix["feedback"]["summary"] = "Очень понравилась загадка!"
    stronger = deepcopy(before)
    stronger["feedback"]["signals"][0]["strength"] = 2

    assert material_evidence_projection(before) == material_evidence_projection(typo_fix)
    assert is_material_evidence_change(before, typo_fix) is False
    assert is_material_evidence_change(before, stronger) is True


def test_vocabulary_digest_is_deterministic_and_content_bound(tmp_path):
    media_root = tmp_path / "media"
    media_root.mkdir()
    vocabulary = media_root / "vocabulary.yaml"
    vocabulary.write_text("schema_version: 1\nterms:\n  story.intrigue: {}\n", encoding="utf-8")

    first = compute_vocabulary_digest(media_root)
    second = compute_vocabulary_digest(media_root)
    vocabulary.write_text(
        "schema_version: 1\nterms:\n  story.intrigue: {}\n  pacing.slow: {}\n",
        encoding="utf-8",
    )

    assert first == second
    assert first.startswith("sha256:")
    assert first != compute_vocabulary_digest(media_root)


def test_metadata_freshness_is_pure_and_classifies_missing_layers():
    current = evaluate_metadata_freshness(work_document())
    missing = work_document()
    missing["identity"].pop("external_ids")
    missing["metadata"]["external"].pop("runtime_min")
    missing["metadata"]["external"].pop("external_metrics")

    assert current == {"identity": "current", "static": "current", "dynamic": "current"}
    assert evaluate_metadata_freshness(missing) == {
        "identity": "missing",
        "static": "current",
        "dynamic": "missing",
    }


def test_semantic_input_digest_ignores_credits_but_tracks_content_facts():
    work = work_document()
    work["metadata"]["external"]["directors"] = [
        {"name": "Director A", "external_ids": {"tmdb": 1}},
    ]
    work["metadata"]["external"]["writers"] = [
        {"name": "Writer A", "external_ids": {"tmdb": 2}},
    ]
    work["metadata"]["external"]["main_cast"] = [
        {"name": "Actor A", "character": "Hero", "external_ids": {"tmdb": 3}},
    ]

    changed_credits = deepcopy(work)
    changed_credits["metadata"]["external"]["directors"] = [
        {"name": "Director B", "external_ids": {"tmdb": 4}},
    ]
    changed_credits["metadata"]["external"]["writers"].reverse()
    changed_credits["metadata"]["external"]["main_cast"].append(
        {"name": "Actor B", "character": "Friend", "external_ids": {"tmdb": 5}}
    )

    changed_synopsis = deepcopy(work)
    changed_synopsis["metadata"]["external"]["synopsis_short"] = "A different story premise."

    vocab_digest = "sha256:" + "a" * 64
    baseline = compute_semantic_input_digest(work, vocab_digest, "media-semantic-v1")

    assert baseline == compute_semantic_input_digest(
        changed_credits, vocab_digest, "media-semantic-v1"
    )
    assert baseline != compute_semantic_input_digest(
        changed_synopsis, vocab_digest, "media-semantic-v1"
    )


def test_semantic_digest_normalizes_synopsis_typography_and_unordered_sets():
    work = work_document()
    work["metadata"]["external"]["countries"] = ["US", "GB"]
    work["metadata"]["external"]["synopsis_short"] = (
        "Ощущения — не что иное, как предупреждения.\n\n"
        "Оказавшись в прошлом, он влюбляется в неё…"
    )

    formatted = deepcopy(work)
    formatted["metadata"]["external"]["genres"] = list(reversed(formatted["metadata"]["external"]["genres"]))
    formatted["metadata"]["external"]["countries"] = ["GB", "US"]
    formatted["metadata"]["external"]["synopsis_short"] = (
        "ощущения - не что иное, как предупреждения. "
        "Оказавшись в прошлом, он влюбляется в нее..."
    )

    changed_content = deepcopy(work)
    changed_content["metadata"]["external"]["synopsis_short"] = (
        "Ощущения — не что иное, как предупреждения. "
        "Оказавшись в прошлом, он НЕ влюбляется в неё."
    )

    vocab_digest = "sha256:" + "a" * 64
    baseline = compute_semantic_input_digest(work, vocab_digest, "media-semantic-v1")

    assert baseline == compute_semantic_input_digest(
        formatted, vocab_digest, "media-semantic-v1"
    )
    assert baseline != compute_semantic_input_digest(
        changed_content, vocab_digest, "media-semantic-v1"
    )
