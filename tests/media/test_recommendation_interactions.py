from datetime import datetime, timezone

from media.commands.schema import parse_command
from media.service.transaction import execute_command
from media.tools.common import iter_jsonl, load_yaml
from tests.media.fixture_repo import copy_fixture_repo

UUID1="123e4567-e89b-42d3-a456-426614174030"
UUID2="123e4567-e89b-42d3-a456-426614174031"


def command(operation_id=UUID1,event="not_tonight",work_ref=None,note="Сегодня хочется легче"):
    return parse_command({
        "schema_version":1,
        "operation_id":operation_id,
        "operation":"record_recommendation_interaction",
        "session_id":"evening-2026-10-03",
        "target":"primary",
        "work_ref":work_ref or {"id":"arrival-2016"},
        "event":event,
        "note":note,
    })


def test_interaction_appends_canonical_jsonl_event(tmp_path):
    root=copy_fixture_repo(tmp_path)
    result=execute_command(root,command(),now=datetime(2026,10,3,20,15,tzinfo=timezone.utc))
    path=root/"media/data/interactions/2026-10.jsonl"
    rows=[row for _,row in iter_jsonl(path)]
    event=rows[-1]
    assert event["id"]==UUID1
    assert event["session_id"]=="evening-2026-10-03"
    assert event["target"]=="primary"
    assert event["type"]=="not_tonight"
    assert event["work_id"]=="arrival-2016"
    assert event["reason"]=="Сегодня хочется легче"
    assert result.status=="applied"


def test_not_tonight_never_changes_stable_interest_or_work_signals(tmp_path):
    root=copy_fixture_repo(tmp_path)
    before=load_yaml(root/"media/data/works/arrival-2016.yaml")
    execute_command(root,command(),now=datetime(2026,10,3,20,15,tzinfo=timezone.utc))
    after=load_yaml(root/"media/data/works/arrival-2016.yaml")
    assert after==before


def test_external_recommendation_can_be_recorded_without_creating_work(tmp_path):
    root=copy_fixture_repo(tmp_path)
    execute_command(root,command(operation_id=UUID2,event="recommended",work_ref={"title":"The Invitation","year":2015}),now=datetime(2026,10,3,20,15,tzinfo=timezone.utc))
    rows=[row for _,row in iter_jsonl(root/"media/data/interactions/2026-10.jsonl")]
    event=rows[-1]
    assert event["work_ref"]=={"title":"The Invitation","year":2015}
    assert "work_id" not in event
    assert not (root/"media/data/works/the-invitation-2015.yaml").exists()


def test_interaction_operation_is_idempotent_by_receipt(tmp_path):
    root=copy_fixture_repo(tmp_path)
    first=execute_command(root,command(),now=datetime(2026,10,3,20,15,tzinfo=timezone.utc))
    count1=len(list(iter_jsonl(root/"media/data/interactions/2026-10.jsonl")))
    second=execute_command(root,command(),now=datetime(2026,10,3,20,16,tzinfo=timezone.utc))
    count2=len(list(iter_jsonl(root/"media/data/interactions/2026-10.jsonl")))
    assert first.status=="applied"
    assert second.status=="already_applied"
    assert count2==count1


def test_interaction_profile_counts_update_without_becoming_affinity(tmp_path):
    root=copy_fixture_repo(tmp_path)
    execute_command(root,command(event="selected"),now=datetime(2026,10,3,20,15,tzinfo=timezone.utc))
    profile=load_yaml(root/"media/generated/profiles/primary.yaml")
    assert profile["summary"]["selected_count"]>=1
    assert all(not any(e.get("source_kind")=="recommendation_interaction" for e in (aff.get("evidence") or [])) for aff in profile["affinities"].values())
