from pathlib import Path

import pytest

from media.commands.schema import parse_command
from media.domain.errors import UnknownTargetError
from media.tools.common import dump_yaml, load_yaml
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo


def request(candidate=None,target="primary",text="Мне это зайдёт?"):
    return parse_command({
        "schema_version":1,
        "operation":"assess_candidate",
        "target":target,
        "candidate":candidate or {"id":"unwatched-fit-2020"},
        "text":text,
    })


def _file_map(root:Path)->dict[str,bytes]:
    return {str(path.relative_to(root)):path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _write_similarity(root:Path,*,external=False):
    path=root/"media/data/relations/similarity/primary.yaml"; path.parent.mkdir(parents=True,exist_ok=True)
    if external:
        left={"kind":"external","provider":"tmdb","media_type":"movie","id":45612,"title":"Source Code","year":2011}
        right={"kind":"canonical","work_id":"arrival-2016"}
    else:
        left={"kind":"canonical","work_id":"arrival-2016"}
        right={"kind":"canonical","work_id":"unwatched-fit-2020"}
    dump_yaml(path,{"schema_version":1,"target":"primary","relations":[{"type":"similar","left":left,"right":right,"terms":["story.intrigue"],"note":"Оба держат интригой","updated_at":"2026-10-03T20:00:00+00:00","provenance":{"source":"explicit"}}]})


def _write_rated_work(
    root: Path,
    work_id: str,
    *,
    primary_rating: float | None = None,
    partner_rating: float | None = None,
    couple_rating: float | None = None,
    fingerprint: bool = False,
) -> None:
    work={
        "schema_version":4,
        "entity_type":"work",
        "id":work_id,
        "identity":{"format":"movie","title_original":work_id,"title_ru":work_id,"year":2026},
        "metadata":{"external":{"runtime_min":100}},
        "viewer_signals":{},
        "group_signals":{},
    }
    if fingerprint:
        work["metadata"]["semantic"]={"traits":[{"term":"story.intrigue","source":"llm_inferred","confidence":"high"}]}
    for target,rating in (("primary",primary_rating),("partner",partner_rating)):
        if rating is not None:
            work["viewer_signals"][target]={
                "viewing":{"status":"watched"},
                "rating":{"score":rating,"source":"explicit","confidence":"exact"},
            }
    if couple_rating is not None:
        work["group_signals"]["couple"]={
            "rating":{"score":couple_rating,"source":"explicit","confidence":"exact"},
        }
    dump_yaml(root/f"media/data/works/{work_id}.yaml",work)


def _supporting_ids(context: dict) -> set[str]:
    ids={item["id"] for item in context["taste_context"]["recent_feedback"]}
    ids.update(item["id"] for item in context["taste_context"]["representative"]["high"])
    ids.update(item["id"] for item in context["taste_context"]["representative"]["low"])
    return ids


def _has_fingerprint(root: Path, work_id: str) -> bool:
    work=load_yaml(root/f"media/data/works/{work_id}.yaml") or {}
    traits=(((work.get("metadata") or {}).get("semantic") or {}).get("traits") or [])
    return any(isinstance(item,dict) and item.get("term") for item in traits)


def test_canonical_candidate_context_contains_fingerprint_similarity_and_taste(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); _write_similarity(root)
    before=_file_map(root)
    from media.service.assessment import build_candidate_assessment_context

    result=build_candidate_assessment_context(root/"media",request())

    assert result["schema_version"]==1
    assert result["target"]=="primary"
    assert result["request"]=={"text":"Мне это зайдёт?"}
    assert result["candidate"]["kind"]=="canonical"
    assert result["candidate"]["id"]=="unwatched-fit-2020"
    assert result["candidate"]["semantic_fingerprint"]==[{"term":"story.intrigue","source":"llm_inferred","confidence":"high"}]
    assert result["similarities"][0]["other"]=={"kind":"canonical","work_id":"arrival-2016"}
    assert result["taste_context"]["target"]=="primary"
    assert _file_map(root)==before


def test_assessment_exposes_top_level_coverage_and_fact_only_limitations(tmp_path):
    root=copy_fixture_repo(tmp_path)
    _write_rated_work(root,"assessment-affinity-source",primary_rating=9.0,fingerprint=True)
    rebuild_generated(root/"media")
    from media.service.assessment import build_candidate_assessment_context

    result=build_candidate_assessment_context(root/"media",request())
    coverage=result["assessment_coverage"]

    assert coverage["candidate_has_fingerprint"] is True
    assert coverage["candidate_directional_matches"] >= 1
    supporting=_supporting_ids(result)
    assert coverage["supporting_works_total"]==len(supporting)
    assert coverage["supporting_works_with_fingerprint"]==sum(_has_fingerprint(root,work_id) for work_id in supporting)
    assert coverage["profile_rated_works_total"] >= coverage["supporting_works_total"]
    assert 0 <= coverage["profile_rated_works_with_fingerprint"] <= coverage["profile_rated_works_total"]
    assert isinstance(result["limitations"],list)
    assert "likely" not in result
    assert "verdict" not in result
    assert "score" not in result


def test_external_candidate_without_fingerprint_has_explicit_basis_limitations(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media")
    from media.service.assessment import build_candidate_assessment_context

    result=build_candidate_assessment_context(root/"media",request(candidate={"tmdb_media_type":"movie","tmdb_id":45612,"title":"Source Code","year":2011}))

    assert result["assessment_coverage"]["candidate_has_fingerprint"] is False
    assert result["assessment_coverage"]["candidate_directional_matches"]==0
    assert result["limitations"][:2]==[
        "no_candidate_semantic_fingerprint",
        "no_candidate_personalized_basis",
    ]


def test_profile_rated_coverage_is_stable_beyond_request_local_support_limits(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media")
    from media.service.assessment import build_candidate_assessment_context

    before=build_candidate_assessment_context(root/"media",request())["assessment_coverage"]
    for index in range(12):
        _write_rated_work(
            root,
            f"assessment-rated-{index:02d}",
            primary_rating=9.0,
            fingerprint=index < 3,
        )
    rebuild_generated(root/"media")

    result=build_candidate_assessment_context(root/"media",request())
    coverage=result["assessment_coverage"]

    assert coverage["profile_rated_works_total"]==before["profile_rated_works_total"]+12
    assert coverage["profile_rated_works_with_fingerprint"]==before["profile_rated_works_with_fingerprint"]+3
    assert coverage["supporting_works_total"] < coverage["profile_rated_works_total"]
    assert "partial_semantic_coverage" in result["limitations"]


def test_couple_profile_rated_set_uses_member_rating_then_direct_group_fallback(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media")
    from media.service.assessment import build_candidate_assessment_context

    before=build_candidate_assessment_context(root/"media",request(target="couple"))["assessment_coverage"]
    _write_rated_work(root,"couple-member-rated",primary_rating=8.0,fingerprint=True)
    _write_rated_work(root,"couple-direct-rated",couple_rating=8.0,fingerprint=False)
    rebuild_generated(root/"media")

    after=build_candidate_assessment_context(root/"media",request(target="couple"))["assessment_coverage"]

    assert after["profile_rated_works_total"]==before["profile_rated_works_total"]+2
    assert after["profile_rated_works_with_fingerprint"]==before["profile_rated_works_with_fingerprint"]+1


def test_stable_external_candidate_uses_snapshot_without_creating_work(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); _write_similarity(root,external=True)
    before=_file_map(root)
    from media.service.assessment import build_candidate_assessment_context

    result=build_candidate_assessment_context(root/"media",request(candidate={"tmdb_media_type":"movie","tmdb_id":45612,"title":"Source Code","year":2011}))

    assert result["candidate"]=={
        "kind":"external",
        "provider":"tmdb",
        "media_type":"movie",
        "id":45612,
        "title":"Source Code",
        "year":2011,
        "semantic_fingerprint":None,
    }
    assert result["similarities"][0]["other"]=={"kind":"canonical","work_id":"arrival-2016"}
    assert not (root/"media/data/works/source-code-2011.yaml").exists()
    assert _file_map(root)==before


def test_candidate_assessment_validates_target(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media")
    from media.service.assessment import build_candidate_assessment_context
    with pytest.raises(UnknownTargetError):
        build_candidate_assessment_context(root/"media",request(target="ghost"))
