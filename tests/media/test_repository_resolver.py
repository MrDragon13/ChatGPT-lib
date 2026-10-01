from __future__ import annotations

import pytest

from media.domain.errors import AmbiguousIdentityError, NotFoundError, UnknownTargetError
from media.domain.types import WorkRef
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_target_kind, resolve_work
from tests.media.fixture_repo import copy_fixture_repo


@pytest.fixture
def repo(tmp_path):
    root = copy_fixture_repo(tmp_path)
    return YamlRepository(root / "media")


def test_resolve_exact_internal_id(repo):
    assert resolve_work(repo, WorkRef(id="arrival-2016")).id == "arrival-2016"


def test_tmdb_identity_uses_media_type_plus_numeric_id(repo):
    assert resolve_work(repo, WorkRef(tmdb_media_type="movie", tmdb_id=42)).id == "movie-42"
    assert resolve_work(repo, WorkRef(tmdb_media_type="tv", tmdb_id=42)).id == "tv-42"


def test_title_ru_and_alternate_titles_resolve(repo):
    assert resolve_work(repo, WorkRef(title="  ПРИБЫТИЕ  ")).id == "arrival-2016"
    assert resolve_work(repo, WorkRef(title="hidden   NAME")).id == "hidden-name-2010"


def test_dune_without_year_returns_ambiguous_candidates(repo):
    with pytest.raises(AmbiguousIdentityError) as exc:
        resolve_work(repo, WorkRef(title="Dune"))
    assert {candidate.year for candidate in exc.value.candidates} == {1984, 2021}
    assert resolve_work(repo, WorkRef(title="Dune", year=2021)).id == "dune-2021"


def test_imdb_resolves_and_unknown_work_is_not_found(repo):
    assert resolve_work(repo, WorkRef(imdb_id="tt2543164")).id == "arrival-2016"
    with pytest.raises(NotFoundError):
        resolve_work(repo, WorkRef(title="Does Not Exist"))


def test_unknown_target_is_rejected(repo):
    assert resolve_target_kind(repo, "primary") == "viewer"
    assert resolve_target_kind(repo, "couple") == "group"
    with pytest.raises(UnknownTargetError):
        resolve_target_kind(repo, "stranger")
