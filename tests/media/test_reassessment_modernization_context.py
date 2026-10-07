from __future__ import annotations

from pathlib import Path

from media.repository.yaml_repo import YamlRepository
from media.service.reassessment import (
    build_reassessment_modernization_context,
    file_sha256,
    ledger_bytes,
    ledger_digest_bytes,
)
from media.tools.common import dump_yaml


def _work(work_id: str, title: str, year: int, *, fetched_at: str = "2026-10-01T00:00:00Z") -> dict:
    return {
        "schema_version": 4,
        "id": work_id,
        "entity_type": "work",
        "identity": {
            "format": "movie",
            "title_original": title,
            "title_ru": title,
            "year": year,
            "external_ids": {
                "tmdb": {"media_type": "movie", "id": year},
                "imdb": f"tt{year}",
            },
        },
        "metadata": {
            "external": {
                "provenance": {"provider": "tmdb", "provider_id": year, "fetched_at": fetched_at}
            },
            "semantic": {
                "traits": [
                    {"term": "story.intrigue", "source": "llm_inferred", "confidence": "high"},
                    {"term": "tone.serious", "source": "llm_inferred", "confidence": "medium"},
                ]
            },
        },
        "viewer_signals": {
            "primary": {
                "rating": {"score": 9, "source": "explicit", "confidence": "exact"},
                "feedback": {"summary": "must stay hidden", "signals": []},
            }
        },
        "provenance": {"created_at": "2026-01-01", "updated_at": "2026-10-01"},
    }


def _repo(tmp_path: Path) -> YamlRepository:
    media = tmp_path / "media"
    dump_yaml(media / "vocabulary.yaml", {
        "schema_version": 1,
        "terms": {
            "story.intrigue": {"kind": "story"},
            "tone.serious": {"kind": "tone"},
        },
    })
    for item in (
        _work("reviewed-b-2021", "Reviewed B", 2021),
        _work("reviewed-a-2020", "Reviewed A", 2020),
        _work("pending-2019", "Pending", 2019),
        _work("blocked-2018", "Blocked", 2018),
        _work("completed-2017", "Completed", 2017),
    ):
        dump_yaml(media / "data" / "works" / f"{item['id']}.yaml", item)
    return YamlRepository(media)


def _ledger() -> dict:
    ids = ["reviewed-b-2021", "reviewed-a-2020", "pending-2019", "blocked-2018", "completed-2017"]
    return {
        "pilot_id": "primary-legacy-v1",
        "frozen_cohort": {
            "work_ids": ids,
            "items": {
                work_id: {"order_rank": rank}
                for rank, work_id in enumerate(ids)
            },
        },
        "items": {
            "reviewed-b-2021": {
                "status": "reviewed",
                "reviewed_at": "2026-10-06T12:00:00Z",
                "outcome": "changed",
            },
            "reviewed-a-2020": {
                "status": "reviewed",
                "reviewed_at": "2026-10-06T11:00:00Z",
                "outcome": "confirmed_unchanged",
            },
            "pending-2019": {"status": "pending"},
            "blocked-2018": {
                "status": "reviewed",
                "reviewed_at": "2026-10-06T10:00:00Z",
                "outcome": "changed",
                "modernization": {
                    "status": "blocked",
                    "blocker_code": "provider_identity_ambiguous",
                    "recorded_at": "2026-10-06T13:00:00Z",
                },
            },
            "completed-2017": {
                "status": "reviewed",
                "reviewed_at": "2026-10-06T09:00:00Z",
                "outcome": "changed",
                "modernization": {
                    "status": "completed",
                    "completed_at": "2026-10-06T14:00:00Z",
                },
            },
        },
        "sessions": [],
    }


def test_modernization_context_returns_only_reviewed_due_items_in_deterministic_order(tmp_path):
    repo = _repo(tmp_path)
    ledger = _ledger()
    context = build_reassessment_modernization_context(repo, ledger)

    assert context["pilot_id"] == "primary-legacy-v1"
    assert context["ledger_digest"] == ledger_digest_bytes(ledger_bytes(ledger))
    assert context["vocabulary_digest"] == file_sha256((repo.media_root / "vocabulary.yaml").read_bytes())
    assert [card["work_id"] for card in context["cards"]] == ["reviewed-a-2020", "reviewed-b-2021"]
    assert all(card["modernization_status"] == "due" for card in context["cards"])


def test_modernization_context_excludes_nonreviewed_completed_and_blocked_by_default(tmp_path):
    repo = _repo(tmp_path)
    context = build_reassessment_modernization_context(repo, _ledger())
    ids = {card["work_id"] for card in context["cards"]}
    assert "pending-2019" not in ids
    assert "completed-2017" not in ids
    assert "blocked-2018" not in ids


def test_modernization_context_can_include_blocked_for_explicit_recovery(tmp_path):
    repo = _repo(tmp_path)
    context = build_reassessment_modernization_context(repo, _ledger(), include_blocked=True)
    blocked = next(card for card in context["cards"] if card["work_id"] == "blocked-2018")
    assert blocked["modernization_status"] == "blocked"
    assert blocked["blocker_code"] == "provider_identity_ambiguous"


def test_modernization_cards_are_factual_and_hide_viewer_evidence(tmp_path):
    repo = _repo(tmp_path)
    context = build_reassessment_modernization_context(repo, _ledger())
    card = next(item for item in context["cards"] if item["work_id"] == "reviewed-a-2020")
    assert card["title"] == "Reviewed A"
    assert card["year"] == 2020
    assert card["reviewed_at"] == "2026-10-06T11:00:00Z"
    assert card["provider_identity"] == {
        "tmdb": {"media_type": "movie", "id": 2020},
        "imdb": "tt2020",
    }
    assert card["provider_fetched_at"] == "2026-10-01T00:00:00Z"
    assert card["semantic_trait_count"] == 2
    assert card["work_digest"] == file_sha256(repo.get_work("reviewed-a-2020").path.read_bytes())
    assert card["vocabulary_digest"] == context["vocabulary_digest"]
    assert set(card) == {
        "work_id", "title", "year", "reviewed_at", "order_rank",
        "provider_identity", "provider_fetched_at", "semantic_trait_count",
        "work_digest", "vocabulary_digest", "modernization_status", "blocker_code",
    }
    assert "must stay hidden" not in repr(card)
    assert "rating" not in repr(card)
    assert "feedback" not in repr(card)


def test_modernization_context_limit_must_be_positive(tmp_path):
    repo = _repo(tmp_path)
    try:
        build_reassessment_modernization_context(repo, _ledger(), limit=0)
    except ValueError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("expected ValueError")
