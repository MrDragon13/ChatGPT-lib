from __future__ import annotations

from pathlib import Path

import yaml

from media.tools.validate import validate_repository
from tests.media.fixture_repo import copy_fixture_repo


def _canonical(work_id: str) -> dict:
    return {"kind": "canonical", "work_id": work_id}


def _external_tmdb(tmdb_id: int, title: str = "Source Code", year: int = 2011) -> dict:
    return {
        "kind": "external",
        "provider": "tmdb",
        "media_type": "movie",
        "id": tmdb_id,
        "title": title,
        "year": year,
    }


def _relation(left: dict, right: dict, *, terms: list[str] | None = None, updated_at: str = "2026-10-03T18:00:00+00:00") -> dict:
    return {
        "type": "similar",
        "left": left,
        "right": right,
        "terms": list(terms or []),
        "note": None,
        "updated_at": updated_at,
        "provenance": {"source": "explicit"},
    }


def _write_similarity(repo_root: Path, target: str, relations: list[dict]) -> None:
    path = repo_root / "media" / "data" / "relations" / "similarity" / f"{target}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "target": target, "relations": relations},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def _codes(repo_root: Path) -> set[str]:
    return {issue.code for issue in validate_repository(repo_root)}


def test_valid_similarity_accepts_canonical_and_stable_external_endpoint(tmp_path: Path):
    repo_root = copy_fixture_repo(tmp_path)
    _write_similarity(
        repo_root,
        "primary",
        [_relation(_canonical("arrival-2016"), _external_tmdb(45612), terms=["story.intrigue"])],
    )

    codes = _codes(repo_root)
    assert "schema" not in codes
    assert "missing_target" not in codes
    assert "missing_ref" not in codes
    assert "vocabulary_unknown" not in codes


def test_similarity_validation_rejects_unknown_target_work_and_term(tmp_path: Path):
    repo_root = copy_fixture_repo(tmp_path)
    _write_similarity(
        repo_root,
        "ghost",
        [_relation(_canonical("missing-work"), _external_tmdb(45612), terms=["story.nonexistent"])],
    )

    codes = _codes(repo_root)
    assert "missing_target" in codes
    assert "missing_ref" in codes
    assert "vocabulary_unknown" in codes


def test_similarity_validation_rejects_self_link_duplicate_reverse_and_noncanonical_order(tmp_path: Path):
    repo_root = copy_fixture_repo(tmp_path)
    first = _relation(_canonical("arrival-2016"), _canonical("dune-2021"))
    reversed_duplicate = _relation(_canonical("dune-2021"), _canonical("arrival-2016"), updated_at="2026-10-03T19:00:00+00:00")
    self_link = _relation(_canonical("arrival-2016"), _canonical("arrival-2016"))
    _write_similarity(repo_root, "primary", [first, reversed_duplicate, self_link])

    codes = _codes(repo_root)
    assert "duplicate_similarity" in codes
    assert "similarity_order" in codes
    assert "self_relation" in codes
