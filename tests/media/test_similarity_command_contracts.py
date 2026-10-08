from __future__ import annotations

import pytest

from media.commands.schema import parse_command
from media.domain.errors import CommandValidationError


VALID_UUID = "123e4567-e89b-42d3-a456-426614174000"


def test_set_work_similarity_accepts_canonical_and_stable_external_refs():
    command = parse_command({
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "set_work_similarity",
        "target": "primary",
        "left": {"id": "deja-vu-2006"},
        "right": {
            "title": "Source Code",
            "year": 2011,
            "tmdb_media_type": "movie",
            "tmdb_id": 45612,
        },
        "terms": ["narrative.time_loop"],
        "note": "Оба строятся вокруг повторного переживания события.",
    })

    assert type(command).__name__ == "SetWorkSimilarityCommand"
    assert command.target == "primary"
    assert command.left.id == "deja-vu-2006"
    assert command.right.tmdb_id == 45612
    assert command.terms == ("narrative.time_loop",)


def test_remove_work_similarity_is_typed():
    command = parse_command({
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "remove_work_similarity",
        "target": "couple",
        "left": {"imdb_id": "tt0453467", "title": "Deja Vu", "year": 2006},
        "right": {"tmdb_media_type": "movie", "tmdb_id": 45612, "title": "Source Code", "year": 2011},
    })

    assert type(command).__name__ == "RemoveWorkSimilarityCommand"
    assert command.target == "couple"
    assert command.left.imdb_id == "tt0453467"
    assert command.right.tmdb_id == 45612


def test_assess_candidate_is_read_only_and_does_not_require_operation_id():
    request = parse_command({
        "schema_version": 1,
        "operation": "assess_candidate",
        "target": "primary",
        "candidate": {"title": "Source Code", "year": 2011},
        "text": "Хочу динамичный фильм на вечер",
    })

    assert type(request).__name__ == "AssessCandidateRequest"
    assert request.target == "primary"
    assert request.candidate.title == "Source Code"
    assert request.text == "Хочу динамичный фильм на вечер"


def test_similarity_write_requires_stable_persistent_external_identity():
    with pytest.raises(CommandValidationError):
        parse_command({
            "schema_version": 1,
            "operation_id": VALID_UUID,
            "operation": "set_work_similarity",
            "target": "primary",
            "left": {"id": "deja-vu-2006"},
            "right": {"title": "Source Code", "year": 2011},
            "terms": [],
            "note": None,
        })


def test_similarity_commands_reject_unknown_fields():
    with pytest.raises(CommandValidationError):
        parse_command({
            "schema_version": 1,
            "operation_id": VALID_UUID,
            "operation": "remove_work_similarity",
            "target": "primary",
            "left": {"id": "deja-vu-2006"},
            "right": {"tmdb_media_type": "movie", "tmdb_id": 45612},
            "unexpected": True,
        })
