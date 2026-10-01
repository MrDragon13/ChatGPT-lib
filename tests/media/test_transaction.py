from datetime import datetime, timezone
from pathlib import Path
import pytest
from media.commands.schema import parse_command
from media.domain.errors import PathPolicyError, TransactionValidationError
from media.service.path_policy import verify_changed_paths
from media.service.transaction import execute_command
from tests.media.fixture_repo import copy_fixture_repo
UUID="123e4567-e89b-42d3-a456-426614174010"
def command(term=None):
    update={"target":"primary","viewing":{"status":"partial"}}
    if term: update["feedback"]={"summary":"x","signals":[{"term":term,"sentiment":"negative","strength":2,"source":"explicit","confidence":"high"}]}
    return parse_command({"schema_version":1,"operation_id":UUID,"operation":"record_viewing_feedback","work_ref":{"id":"arrival-2016"},"target_updates":[update]})
def snapshot(root:Path): return {str(p.relative_to(root)):p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}
def test_same_operation_id_returns_already_applied_without_second_effect(tmp_path):
    root=copy_fixture_repo(tmp_path); cmd=command(); first=execute_command(root,cmd,now=datetime(2026,10,1,tzinfo=timezone.utc)); after=snapshot(root); second=execute_command(root,cmd,now=datetime(2026,10,2,tzinfo=timezone.utc)); assert first.status=="applied"; assert second.status=="already_applied"; assert snapshot(root)==after
def test_invalid_vocabulary_term_leaves_original_tree_byte_identical(tmp_path):
    root=copy_fixture_repo(tmp_path); before=snapshot(root)
    with pytest.raises(TransactionValidationError): execute_command(root,command("missing.term"),now=datetime(2026,10,1,tzinfo=timezone.utc))
    assert snapshot(root)==before
def test_path_policy_rejects_schema_and_service_paths():
    with pytest.raises(PathPolicyError): verify_changed_paths("record_viewing_feedback",["media/schemas/work.schema.json"])
    with pytest.raises(PathPolicyError): verify_changed_paths("record_viewing_feedback",["media/service/mutate.py"])
    verify_changed_paths("record_viewing_feedback",["media/data/works/arrival-2016.yaml","media/generated/index.jsonl","media/generated/profiles/primary.yaml"])
