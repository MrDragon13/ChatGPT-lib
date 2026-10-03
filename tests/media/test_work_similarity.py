from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from media.commands.schema import parse_command
from media.domain.errors import CommandValidationError, UnknownTargetError
from media.service.transaction import execute_command
from media.tools.common import load_yaml
from tests.media.fixture_repo import copy_fixture_repo


UUID1 = "123e4567-e89b-42d3-a456-426614174040"
UUID2 = "123e4567-e89b-42d3-a456-426614174041"
UUID3 = "123e4567-e89b-42d3-a456-426614174042"
UUID4 = "123e4567-e89b-42d3-a456-426614174043"
NOW = datetime(2026, 10, 3, 20, 15, tzinfo=timezone.utc)


def _set(operation_id=UUID1, *, target="primary", left=None, right=None, terms=None, note="Похожи по интриге"):
    return parse_command({
        "schema_version": 1,
        "operation_id": operation_id,
        "operation": "set_work_similarity",
        "target": target,
        "left": left or {"id": "arrival-2016"},
        "right": right or {"id": "dune-2021"},
        "terms": list(terms if terms is not None else ["story.intrigue"]),
        "note": note,
    })


def _remove(operation_id=UUID4, *, target="primary", left=None, right=None):
    return parse_command({
        "schema_version": 1,
        "operation_id": operation_id,
        "operation": "remove_work_similarity",
        "target": target,
        "left": left or {"id": "arrival-2016"},
        "right": right or {"id": "dune-2021"},
    })


def _doc(root: Path, target="primary"):
    return load_yaml(root / "media" / "data" / "relations" / "similarity" / f"{target}.yaml")


def test_set_similarity_persists_one_normalized_canonical_pair(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)

    result = execute_command(root, _set(), now=NOW)

    relation = _doc(root)["relations"][0]
    assert result.status == "applied"
    assert relation["left"] == {"kind": "canonical", "work_id": "arrival-2016"}
    assert relation["right"] == {"kind": "canonical", "work_id": "dune-2021"}
    assert relation["terms"] == ["story.intrigue"]
    assert relation["note"] == "Похожи по интриге"
    assert relation["updated_at"] == NOW.isoformat()
    assert relation["provenance"] == {"source": "explicit"}


def test_known_external_identity_normalizes_to_existing_canonical_work(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)

    execute_command(
        root,
        _set(
            right={
                "tmdb_media_type": "movie",
                "tmdb_id": 42,
                "title": "Movie Forty Two",
                "year": 2001,
            }
        ),
        now=NOW,
    )

    relation = _doc(root)["relations"][0]
    assert {relation["left"]["work_id"], relation["right"]["work_id"]} == {"arrival-2016", "movie-42"}
    assert relation["left"]["kind"] == relation["right"]["kind"] == "canonical"


def test_unknown_external_identity_is_persisted_without_creating_library_work(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)

    execute_command(
        root,
        _set(
            right={
                "tmdb_media_type": "movie",
                "tmdb_id": 45612,
                "title": "Source Code",
                "year": 2011,
            }
        ),
        now=NOW,
    )

    relation = _doc(root)["relations"][0]
    endpoints = [relation["left"], relation["right"]]
    external = next(item for item in endpoints if item["kind"] == "external")
    assert external == {
        "kind": "external",
        "provider": "tmdb",
        "media_type": "movie",
        "id": 45612,
        "title": "Source Code",
        "year": 2011,
    }
    assert not (root / "media" / "data" / "works" / "source-code-2011.yaml").exists()


def test_external_to_external_similarity_is_supported(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)

    execute_command(
        root,
        _set(
            left={"imdb_id": "tt1111111", "title": "External A", "year": 2010},
            right={"tmdb_media_type": "movie", "tmdb_id": 99999, "title": "External B", "year": 2012},
        ),
        now=NOW,
    )

    relation = _doc(root)["relations"][0]
    assert relation["left"]["kind"] == "external"
    assert relation["right"]["kind"] == "external"


def test_reverse_order_and_repeated_assertion_upsert_one_current_relation(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    execute_command(root, _set(operation_id=UUID1), now=NOW)
    later = datetime(2026, 10, 3, 21, 0, tzinfo=timezone.utc)

    execute_command(
        root,
        _set(
            operation_id=UUID2,
            left={"id": "dune-2021"},
            right={"id": "arrival-2016"},
            terms=[],
            note="Теперь причина сформулирована иначе",
        ),
        now=later,
    )

    relations = _doc(root)["relations"]
    assert len(relations) == 1
    assert relations[0]["left"] == {"kind": "canonical", "work_id": "arrival-2016"}
    assert relations[0]["right"] == {"kind": "canonical", "work_id": "dune-2021"}
    assert relations[0]["terms"] == []
    assert relations[0]["note"] == "Теперь причина сформулирована иначе"
    assert relations[0]["updated_at"] == later.isoformat()


def test_remove_similarity_is_symmetric_and_idempotent(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    execute_command(root, _set(), now=NOW)

    first = execute_command(
        root,
        _remove(left={"id": "dune-2021"}, right={"id": "arrival-2016"}),
        now=NOW,
    )
    second = execute_command(
        root,
        _remove(operation_id=UUID3, left={"id": "arrival-2016"}, right={"id": "dune-2021"}),
        now=NOW,
    )

    assert first.status == "applied"
    assert _doc(root)["relations"] == []
    assert second.status == "no_change"


def test_similarity_rejects_unknown_target_before_writing(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    with pytest.raises(UnknownTargetError):
        execute_command(root, _set(target="ghost"), now=NOW)
    assert not (root / "media" / "data" / "relations" / "similarity" / "ghost.yaml").exists()


def test_similarity_rejects_unknown_vocabulary_term_before_writing(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    with pytest.raises(CommandValidationError):
        execute_command(root, _set(terms=["story.nonexistent"]), now=NOW)
    assert not (root / "media" / "data" / "relations" / "similarity" / "primary.yaml").exists()
