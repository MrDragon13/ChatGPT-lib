from importlib import import_module

from media.repository.index_repo import IndexRepository
from media.repository.yaml_repo import YamlRepository
from tests.media.fixture_repo import copy_fixture_repo, prepare_derived


def _pool_module():
    return import_module("media.service.recommendation_pool")


def _row(
    work_id,
    *,
    runtime_min=100,
    primary_viewing=None,
    partner_viewing=None,
    interest_state="candidate",
):
    viewer = {}
    if primary_viewing is not None:
        viewer["primary"] = {"viewing": primary_viewing}
    if partner_viewing is not None:
        viewer["partner"] = {"viewing": partner_viewing}
    interest = {}
    if interest_state is not None:
        interest["primary"] = {"state": interest_state}
        interest["couple"] = {"state": interest_state}
    return {
        "id": work_id,
        "runtime_min": runtime_min,
        "viewer": viewer,
        "interest": interest,
    }


def test_eligible_local_candidates_matches_current_primary_filters():
    pool = _pool_module()
    rows = [
        _row("eligible"),
        _row("watched", primary_viewing="watched"),
        _row("not-interested", interest_state="not_interested"),
        _row("too-long", runtime_min=160),
    ]

    result = pool.filter_eligible_candidate_rows(
        rows,
        target="primary",
        viewers={"primary", "partner"},
        groups={"couple": ["primary", "partner"]},
        only_unwatched=True,
        include_not_interested=False,
        runtime_max=120,
    )

    assert [row["id"] for row in result] == ["eligible"]


def test_eligible_local_candidates_group_excludes_only_when_all_members_watched():
    pool = _pool_module()
    rows = [
        _row("both-watched", primary_viewing="watched", partner_viewing="watched"),
        _row("primary-only", primary_viewing="watched", partner_viewing="planned"),
        _row("partner-only", primary_viewing="planned", partner_viewing="watched"),
    ]

    result = pool.filter_eligible_candidate_rows(
        rows,
        target="couple",
        viewers={"primary", "partner"},
        groups={"couple": ["primary", "partner"]},
        only_unwatched=True,
        include_not_interested=False,
        runtime_max=None,
    )

    assert [row["id"] for row in result] == ["primary-only", "partner-only"]


def test_eligible_local_candidates_preserves_runtime_interest_flags_and_order():
    pool = _pool_module()
    rows = [
        _row("first", runtime_min=140, primary_viewing="watched", interest_state="not_interested"),
        _row("second", runtime_min=90),
        _row("third", runtime_min=None),
    ]

    unrestricted = pool.filter_eligible_candidate_rows(
        rows,
        target="primary",
        viewers={"primary", "partner"},
        groups={"couple": ["primary", "partner"]},
        only_unwatched=False,
        include_not_interested=True,
        runtime_max=None,
    )
    bounded = pool.filter_eligible_candidate_rows(
        rows,
        target="primary",
        viewers={"primary", "partner"},
        groups={"couple": ["primary", "partner"]},
        only_unwatched=False,
        include_not_interested=True,
        runtime_max=100,
    )

    assert [row["id"] for row in unrestricted] == ["first", "second", "third"]
    assert [row["id"] for row in bounded] == ["second", "third"]


def test_pure_filter_matches_runtime_wrapper_for_same_rows(tmp_path):
    pool = _pool_module()
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    media_root = root / "media"
    repo = YamlRepository(media_root)
    viewers, groups = repo.configured_targets()
    rows = list(IndexRepository(media_root / "generated" / "index.jsonl").rows())

    direct = pool.filter_eligible_candidate_rows(
        rows,
        target="couple",
        viewers=viewers,
        groups=groups,
        only_unwatched=True,
        include_not_interested=False,
        runtime_max=120,
    )
    wrapped = pool.eligible_local_candidates(
        media_root,
        target="couple",
        only_unwatched=True,
        include_not_interested=False,
        runtime_max=120,
    )

    assert [row["id"] for row in direct] == [row["id"] for row in wrapped]
