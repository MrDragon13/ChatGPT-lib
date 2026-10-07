from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import media.service.media_entry as media_entry_service
import media.service.transaction as transaction
from media.cli import main
from media.commands.schema import parse_command
from media.domain.digests import compute_viewer_digest
from media.service.reanalysis_status import snapshot_evidence
from media.tools.common import dump_yaml, load_yaml
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import append_material_rating_event, copy_fixture_repo


NOW = datetime(2026, 10, 7, 18, 0, tzinfo=timezone.utc)


class ForbiddenProvider:
    def fetch_work(self, *args, **kwargs):
        raise AssertionError("existing-work record_media_entry must not call provider")

    def search_work(self, *args, **kwargs):
        raise AssertionError("existing-work record_media_entry must not search provider")

    def find_by_imdb(self, *args, **kwargs):
        raise AssertionError("existing-work record_media_entry must not call provider")


def _entry_payload(root: Path, *, operation_id: str, event_id: str, rating: float = 9.0) -> dict:
    work=load_yaml(root/"media/data/works/arrival-2016.yaml")
    return {
        "schema_version":1,
        "operation_id":operation_id,
        "idempotency_key":event_id,
        "operation":"record_media_entry",
        "work_ref":{"id":"arrival-2016"},
        "create_if_missing":False,
        "target_updates":[{
            "target":"primary",
            "rating":{"score":rating,"source":"explicit","confidence":"exact"},
        }],
        "preconditions":{
            "expected_viewer_digests":{
                "primary":compute_viewer_digest(work,"primary"),
            },
        },
    }


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
    return path


def _media_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)):path.read_bytes()
        for path in sorted((root/"media").rglob("*"))
        if path.is_file()
    }


def test_existing_media_entry_fast_path_has_zero_external_or_semantic_work_and_single_dirty_rebuilds(tmp_path, monkeypatch):
    root=copy_fixture_repo(tmp_path)
    rebuild_generated(root/"media")
    command=parse_command(_entry_payload(
        root,
        operation_id="123e4567-e89b-42d3-a456-426614175001",
        event_id="123e4567-e89b-42d3-a456-426614175101",
    ))

    def forbidden_semantic(*args, **kwargs):
        raise AssertionError("existing-work record_media_entry must not recompute semantics")

    def forbidden_metadata_refresh(*args, **kwargs):
        raise AssertionError("existing-work record_media_entry must not refresh metadata")

    monkeypatch.setattr(media_entry_service,"compute_semantic_input_digest",forbidden_semantic)
    monkeypatch.setattr(media_entry_service,"compute_vocabulary_digest",forbidden_semantic)
    monkeypatch.setattr(transaction,"plan_refresh_work_metadata",forbidden_metadata_refresh)

    calls={"plan":0,"sync":0,"index":0,"profiles":[]}
    real_plan=transaction._plan
    real_sync=transaction._sync_with_rollback
    real_index=transaction.write_index
    real_profile=transaction.build_profile

    def counted_plan(*args, **kwargs):
        calls["plan"]+=1
        return real_plan(*args, **kwargs)

    def counted_sync(*args, **kwargs):
        calls["sync"]+=1
        return real_sync(*args, **kwargs)

    def counted_index(*args, **kwargs):
        calls["index"]+=1
        return real_index(*args, **kwargs)

    def counted_profile(media_root, target):
        calls["profiles"].append(target)
        return real_profile(media_root,target)

    monkeypatch.setattr(transaction,"_plan",counted_plan)
    monkeypatch.setattr(transaction,"_sync_with_rollback",counted_sync)
    monkeypatch.setattr(transaction,"write_index",counted_index)
    monkeypatch.setattr(transaction,"build_profile",counted_profile)

    result=transaction.execute_command(root,command,provider=ForbiddenProvider(),now=NOW)

    assert result.status=="applied"
    assert calls["plan"]==1
    assert calls["sync"]==1
    assert calls["index"]==1
    assert calls["profiles"].count("primary")==1
    assert calls["profiles"].count("couple")==1
    assert calls["profiles"].count("partner")==0
    assert len(calls["profiles"])==len(set(calls["profiles"]))


def test_no_change_media_entry_does_not_append_history_or_rebuild_generated(tmp_path, monkeypatch):
    root=copy_fixture_repo(tmp_path)
    rebuild_generated(root/"media")
    before_work=(root/"media/data/works/arrival-2016.yaml").read_bytes()
    before_generated={
        str(path.relative_to(root)):path.read_bytes()
        for path in sorted((root/"media/generated").rglob("*"))
        if path.is_file()
    }
    work=load_yaml(root/"media/data/works/arrival-2016.yaml")
    payload={
        "schema_version":1,
        "operation_id":"123e4567-e89b-42d3-a456-426614175002",
        "idempotency_key":"123e4567-e89b-42d3-a456-426614175102",
        "operation":"record_media_entry",
        "work_ref":{"id":"arrival-2016"},
        "create_if_missing":False,
        "target_updates":[{"target":"primary","viewing":{"status":"watched"}}],
        "preconditions":{
            "expected_viewer_digests":{
                "primary":compute_viewer_digest(work,"primary"),
            },
        },
    }

    def forbidden_rebuild(*args, **kwargs):
        raise AssertionError("no_change must not rebuild generated outputs")

    monkeypatch.setattr(transaction,"write_index",forbidden_rebuild)
    monkeypatch.setattr(transaction,"build_profile",forbidden_rebuild)

    result=transaction.execute_command(root,parse_command(payload),provider=ForbiddenProvider(),now=NOW)

    after_generated={
        str(path.relative_to(root)):path.read_bytes()
        for path in sorted((root/"media/generated").rglob("*"))
        if path.is_file()
    }
    assert result.status=="no_change"
    assert (root/"media/data/works/arrival-2016.yaml").read_bytes()==before_work
    assert after_generated==before_generated
    assert (load_yaml(root/"media/data/works/arrival-2016.yaml")["viewer_signals"]["primary"].get("history") or [])==[]


def test_record_media_entry_cli_dry_run_and_apply_have_local_parity(tmp_path, monkeypatch, capsys):
    root=copy_fixture_repo(tmp_path)
    rebuild_generated(root/"media")
    request=_write_json(
        root/"record-media-entry.json",
        _entry_payload(
            root,
            operation_id="123e4567-e89b-42d3-a456-426614175003",
            event_id="123e4567-e89b-42d3-a456-426614175103",
        ),
    )
    monkeypatch.chdir(root)
    monkeypatch.delenv("TMDB_READ_TOKEN",raising=False)
    before=_media_snapshot(root)

    assert main(["apply-command",str(request),"--dry-run","--format","json"])==0
    dry=json.loads(capsys.readouterr().out)
    assert dry["operation"]=="record_media_entry"
    assert dry["status"]=="planned"
    assert _media_snapshot(root)==before

    assert main(["apply-command",str(request),"--format","json"])==0
    applied=json.loads(capsys.readouterr().out)
    assert applied["operation"]=="record_media_entry"
    assert applied["status"]=="applied"


def test_v6_inferred_preferences_cli_dry_run_and_apply_have_local_parity(tmp_path, monkeypatch, capsys):
    root=copy_fixture_repo(tmp_path)
    append_material_rating_event(
        root,
        score=8.5,
        event_id="123e4567-e89b-42d3-a456-426614175104",
        at="2026-10-07T18:00:00Z",
    )
    snapshot=snapshot_evidence(root/"media","primary")
    request=_write_json(root/"set-inferred-v6.json",{
        "schema_version":1,
        "operation_id":"123e4567-e89b-42d3-a456-426614175004",
        "operation":"set_inferred_preferences",
        "target":"primary",
        "hypotheses":[],
        "analysis":{
            "evidence_checkpoint":{
                "material_event_count":snapshot.checkpoint.material_event_count,
                "material_event_prefix_digest":snapshot.checkpoint.material_event_prefix_digest,
            },
            "evidence_digest":snapshot.evidence_digest,
            "algorithm_version":"media-taste-v1",
        },
    })
    monkeypatch.chdir(root)
    before=_media_snapshot(root)

    assert main(["apply-command",str(request),"--dry-run","--format","json"])==0
    dry=json.loads(capsys.readouterr().out)
    assert dry["operation"]=="set_inferred_preferences"
    assert dry["status"]=="planned"
    assert _media_snapshot(root)==before
    assert not (root/"media/preferences/inferred/primary.yaml").exists()

    assert main(["apply-command",str(request),"--format","json"])==0
    applied=json.loads(capsys.readouterr().out)
    assert applied["operation"]=="set_inferred_preferences"
    assert applied["status"]=="applied"
    inferred=load_yaml(root/"media/preferences/inferred/primary.yaml")
    assert inferred["analysis"]["algorithm_version"]=="media-taste-v1"
