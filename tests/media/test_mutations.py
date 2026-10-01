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
