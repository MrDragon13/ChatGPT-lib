from __future__ import annotations

from pathlib import Path

from media.repository.canonical import WorkRecord
from media.service.reassessment import (
    build_reassessment_context,
    build_reassessment_history,
    ledger_bytes,
    ledger_digest_bytes,
)


class FakeRepo:
    def __init__(self, records):
        self._records = {record.id: record for record in records}

    def get_work(self, work_id: str):
        return self._records.get(work_id)

    def iter_works(self):
        yield from self._records.values()


def _record() -> WorkRecord:
    return WorkRecord(
        Path("/repo/media/data/works/batman-2022.yaml"),
        {
            "id": "batman-2022",
            "identity": {
                "title_original": "The Batman",
                "title_ru": "Бэтмен",
                "year": 2022,
            },
            "metadata": {
                "external": {
                    "synopsis_short": "Брюс Уэйн расследует серию убийств в Готэме.",
                    "directors": [{"name": "Мэтт Ривз"}],
                    "main_cast": [{"name": "Роберт Паттинсон", "character": "Bruce Wayne"}],
                },
                "semantic": {
                    "traits": [
                        {"term": "tone.dark", "source": "llm_inferred", "confidence": "high"}
                    ]
                },
            },
            "viewer_signals": {
                "primary": {
                    "viewing": {"status": "watched"},
                    "rating": {"score": 6, "source": "explicit", "confidence": "exact"},
                    "reaction": {"value": "mixed", "source": "explicit", "confidence": "high"},
                    "feedback": {
                        "summary": "Не особо понравился.",
                        "signals": [{"term": "pacing.slow"}],
                    },
                    "history": [
                        {
                            "at": "2026-10-01T00:00:00Z",
                            "previous": {"rating": {"score": 5}},
                            "current": {"rating": {"score": 6}},
                        }
                    ],
                }
            },
        },
    )


def _ledger(*, status: str = "pending") -> dict:
    item = {"status": status}
    if status == "in_progress":
        item.update(
            {
                "session_id": "123e4567-e89b-42d3-a456-426614174001",
                "reserved_at": "2026-10-05T12:00:00Z",
                "pre_review_feedback_digest": "sha256:" + "1" * 64,
                "pre_review_work_file_digest": "sha256:" + "2" * 64,
            }
        )
    sessions = []
    if status == "in_progress":
        sessions = [
            {
                "session_id": item["session_id"],
                "reserved_work_ids": ["batman-2022"],
                "status": "open",
                "opened_at": "2026-10-05T12:00:00Z",
            }
        ]
    return {
        "pilot_id": "primary-legacy-v1",
        "frozen_cohort": {
            "work_ids": ["batman-2022"],
            "items": {"batman-2022": {"order_rank": 0}},
        },
        "items": {"batman-2022": item},
        "sessions": sessions,
    }


def test_reassessment_context_is_unanchored_and_contains_only_safe_memory_fields():
    document = _ledger()
    context = build_reassessment_context(FakeRepo([_record()]), document, limit=5)

    assert context["pilot_id"] == "primary-legacy-v1"
    assert context["ledger_digest"] == ledger_digest_bytes(ledger_bytes(document))
    assert context["open_session"] is None
    assert len(context["cards"]) == 1

    card = context["cards"][0]
    assert card == {
        "work_id": "batman-2022",
        "title": "Бэтмен",
        "year": 2022,
        "synopsis_short": "Брюс Уэйн расследует серию убийств в Готэме.",
        "directors": ["Мэтт Ривз"],
        "main_cast": ["Роберт Паттинсон"],
        "queue_status": "pending",
        "order_rank": 0,
    }

    serialized = repr(card)
    for forbidden in (
        "rating",
        "reaction",
        "feedback",
        "semantic",
        "tone.dark",
        "pacing.slow",
        "Не особо понравился",
        "score",
    ):
        assert forbidden not in serialized


def test_reassessment_context_resumes_open_session_before_pending_queue():
    document = _ledger(status="in_progress")
    context = build_reassessment_context(FakeRepo([_record()]), document, limit=5)

    assert context["open_session"] == {
        "session_id": "123e4567-e89b-42d3-a456-426614174001",
        "reserved_work_ids": ["batman-2022"],
    }
    assert context["cards"][0]["queue_status"] == "in_progress"


def test_reassessment_history_is_explicit_second_phase_and_excludes_semantics():
    history = build_reassessment_history(FakeRepo([_record()]), "batman-2022")

    assert history["work_id"] == "batman-2022"
    assert history["viewer_evidence"]["rating"]["score"] == 6
    assert history["viewer_evidence"]["feedback"]["summary"] == "Не особо понравился."
    assert history["viewer_evidence"]["history"][0]["previous"]["rating"]["score"] == 5
    assert "metadata" not in history
    assert "semantic" not in repr(history)
