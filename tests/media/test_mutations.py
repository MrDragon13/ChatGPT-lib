from datetime import datetime, timezone

import pytest

from media.commands.schema import parse_command
from media.domain.errors import CommandValidationError
from media.service.transaction import execute_command
from media.tools.common import load_yaml
from tests.media.fixture_repo import copy_fixture_repo

UUID1="123e4567-e89b-42d3-a456-426614174001"; UUID2="123e4567-e89b-42d3-a456-426614174002"; UUID3="123e4567-e89b-42d3-a456-426614174003"


def feedback(operation_id=UUID1,target="primary",**parts):
    update={"target":target}; update.update(parts); return parse_command({"schema_version":1,"operation_id":operation_id,"operation":"record_viewing_feedback","work_ref":{"id":"arrival-2016"},"target_updates":[update]})


def edit(operation_id=UUID3,target="primary",set_values=None,clear=None,purge=False):
    item={"target":target}
    if set_values is not None: item["set"]=set_values
    if clear is not None: item["clear"]=clear
    if purge: item["purge"]=True
    return parse_command({"schema_version":1,"operation_id":operation_id,"operation":"edit_viewing_feedback","work_ref":{"id":"arrival-2016"},"target_edits":[item]})


def test_record_feedback_merges_only_supplied_components(tmp_path):
    root=copy_fixture_repo(tmp_path); result=execute_command(root,feedback(rating={"score":8.5,"source":"explicit_approx","confidence":"high"}),now=datetime(2026,10,1,tzinfo=timezone.utc)); signal=load_yaml(root/"media/data/works/arrival-2016.yaml")["viewer_signals"]["primary"]; assert signal["rating"]["score"]==8.5; assert signal["viewing"]["status"]=="watched"; assert "reaction" not in signal; assert result.status=="applied"


def test_changed_existing_signal_appends_one_history_entry(tmp_path):
    root=copy_fixture_repo(tmp_path); execute_command(root,feedback(operation_id=UUID2,viewing={"status":"partial"}),now=datetime(2026,10,1,tzinfo=timezone.utc)); signal=load_yaml(root/"media/data/works/arrival-2016.yaml")["viewer_signals"]["primary"]; assert signal["viewing"]["status"]=="partial"; assert len(signal["history"])==1; assert signal["history"][0]["previous"]=={"viewing":{"status":"watched"}}; assert signal["history"][0]["current"]=={"viewing":{"status":"partial"}}


def test_first_signal_component_write_appends_history_entry(tmp_path):
    root=copy_fixture_repo(tmp_path); execute_command(root,feedback(operation_id=UUID2,target="partner",rating={"score":8.0,"source":"explicit","confidence":"high"}),now=datetime(2026,10,1,tzinfo=timezone.utc)); signal=load_yaml(root/"media/data/works/arrival-2016.yaml")["viewer_signals"]["partner"]; entry=signal["history"][-1]; assert entry["at"]=="2026-10-01T00:00:00Z"; assert entry["previous"]=={}; assert entry["current"]=={"rating":{"score":8.0,"source":"explicit","confidence":"high"}}


def test_noop_feedback_does_not_append_history(tmp_path):
    root=copy_fixture_repo(tmp_path); execute_command(root,feedback(operation_id=UUID2,viewing={"status":"watched"}),now=datetime(2026,10,1,tzinfo=timezone.utc)); signal=load_yaml(root/"media/data/works/arrival-2016.yaml")["viewer_signals"]["primary"]; assert len(signal.get("history", []))==0


def test_group_target_rejects_viewing_patch(tmp_path):
    root=copy_fixture_repo(tmp_path)
    with pytest.raises(CommandValidationError): execute_command(root,feedback(operation_id=UUID3,target="couple",viewing={"status":"watched"}))


def test_set_interest_clears_priority_for_not_interested(tmp_path):
    root=copy_fixture_repo(tmp_path); command=parse_command({"schema_version":1,"operation_id":UUID3,"operation":"set_interest","work_ref":{"id":"unwatched-fit-2020"},"target":"primary","state":"not_interested","priority":5}); execute_command(root,command,now=datetime(2026,10,1,tzinfo=timezone.utc)); interest=load_yaml(root/"media/data/works/unwatched-fit-2020.yaml")["target_states"]["primary"]["interest"]; assert interest=={"state":"not_interested"}


def test_edit_feedback_can_rerate_and_preserve_viewing(tmp_path):
    root=copy_fixture_repo(tmp_path)
    execute_command(root, feedback(operation_id=UUID1, rating={"score":7.0,"source":"explicit","confidence":"exact"}), now=datetime(2026,10,1,tzinfo=timezone.utc))
    execute_command(root, edit(operation_id=UUID2, set_values={"rating":{"score":9.0,"source":"explicit","confidence":"exact"}}), now=datetime(2026,10,2,tzinfo=timezone.utc))
    signal=load_yaml(root/"media/data/works/arrival-2016.yaml")["viewer_signals"]["primary"]
    assert signal["rating"]["score"] == 9.0
    assert signal["viewing"]["status"] == "watched"
    assert signal["history"][-1]["previous"]["rating"]["score"] == 7.0
    assert signal["history"][-1]["current"]["rating"]["score"] == 9.0


def test_edit_feedback_clear_rating_preserves_feedback_and_history(tmp_path):
    root=copy_fixture_repo(tmp_path)
    execute_command(root, feedback(operation_id=UUID1, rating={"score":8.0,"source":"explicit","confidence":"exact"}, feedback={"summary":"Интрига понравилась","signals":[{"term":"story.intrigue","sentiment":"positive","strength":2,"source":"explicit","confidence":"high"}]}), now=datetime(2026,10,1,tzinfo=timezone.utc))
    execute_command(root, edit(operation_id=UUID2, clear=["rating"]), now=datetime(2026,10,2,tzinfo=timezone.utc))
    signal=load_yaml(root/"media/data/works/arrival-2016.yaml")["viewer_signals"]["primary"]
    assert "rating" not in signal
    assert signal["feedback"]["summary"] == "Интрига понравилась"
    assert signal["viewing"]["status"] == "watched"
    assert signal["history"][-1]["previous"]["rating"]["score"] == 8.0
    assert signal["history"][-1]["current"] == {"rating": None}


def test_edit_feedback_clear_missing_component_is_noop(tmp_path):
    root=copy_fixture_repo(tmp_path)
    result=execute_command(root, edit(operation_id=UUID2, clear=["reaction"]), now=datetime(2026,10,2,tzinfo=timezone.utc))
    signal=load_yaml(root/"media/data/works/arrival-2016.yaml")["viewer_signals"]["primary"]
    assert result.status == "no_change"
    assert "history" not in signal


def test_edit_feedback_rejects_set_and_clear_same_component(tmp_path):
    root=copy_fixture_repo(tmp_path)
    command=edit(operation_id=UUID2, set_values={"rating":{"score":9.0,"source":"explicit","confidence":"exact"}}, clear=["rating"])
    with pytest.raises(CommandValidationError):
        execute_command(root, command)


def test_edit_feedback_group_rejects_viewing_set_or_clear(tmp_path):
    root=copy_fixture_repo(tmp_path)
    with pytest.raises(CommandValidationError):
        execute_command(root, edit(operation_id=UUID2,target="couple",set_values={"viewing":{"status":"watched"}}))
    with pytest.raises(CommandValidationError):
        execute_command(root, edit(operation_id=UUID3,target="couple",clear=["viewing"]))


def test_edit_feedback_explicit_purge_removes_entire_target_signal(tmp_path):
    root=copy_fixture_repo(tmp_path)
    execute_command(root, feedback(operation_id=UUID1, rating={"score":8.0,"source":"explicit","confidence":"exact"}), now=datetime(2026,10,1,tzinfo=timezone.utc))
    result=execute_command(root, edit(operation_id=UUID2, purge=True), now=datetime(2026,10,2,tzinfo=timezone.utc))
    work=load_yaml(root/"media/data/works/arrival-2016.yaml")
    assert "primary" not in (work.get("viewer_signals") or {})
    assert result.status == "applied"


def test_edit_feedback_rejects_purge_combined_with_set_or_clear(tmp_path):
    root=copy_fixture_repo(tmp_path)
    command=edit(operation_id=UUID2, set_values={"rating":{"score":9.0,"source":"explicit","confidence":"exact"}}, purge=True)
    with pytest.raises(CommandValidationError):
        execute_command(root, command)
