from pathlib import Path

import pytest

from media.commands.schema import parse_command
from media.domain.errors import UnknownTargetError
from media.tools.common import dump_yaml
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
