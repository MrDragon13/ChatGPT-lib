from __future__ import annotations

import json
from pathlib import Path

from media.cli import main
from media.domain.digests import compute_viewer_digest
from media.tools.common import load_yaml
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo

UUID="123e4567-e89b-42d3-a456-426614174201"

def _write_json(path:Path,data:dict)->Path: path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8"); return path
def _feedback_command(root:Path,path:Path)->Path:
    work=load_yaml(root/"media/data/works/arrival-2016.yaml")
    return _write_json(path,{
        "schema_version":1,
        "operation_id":UUID,
        "idempotency_key":UUID,
        "operation":"record_media_entry",
        "work_ref":{"id":"arrival-2016"},
        "create_if_missing":False,
        "target_updates":[{"target":"primary","rating":{"score":8.5,"source":"explicit_approx","confidence":"high"}}],
        "preconditions":{"expected_viewer_digests":{"primary":compute_viewer_digest(work,"primary")}},
    })
def test_apply_command_dry_run_changes_nothing(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_feedback_command(root,root/"request.json"); before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}; monkeypatch.chdir(root); assert main(["apply-command",str(request),"--dry-run","--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="planned"; after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}; assert after==before
def test_apply_command_json_reports_status_entities_and_files(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_feedback_command(root,root/"request.json"); monkeypatch.chdir(root); assert main(["apply-command",str(request),"--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="applied"; assert result["changed_entities"]==["arrival-2016"]; assert "media/data/works/arrival-2016.yaml" in result["changed_files"]; assert any(path.startswith(".media/operations/") for path in result["changed_files"])
def test_add_existing_work_reports_no_change_without_tmdb_token(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_write_json(root/"add.json",{"schema_version":1,"operation_id":"123e4567-e89b-42d3-a456-426614174202","operation":"add_work","work_ref":{"title":"Arrival","year":2016}}); monkeypatch.chdir(root); monkeypatch.delenv("TMDB_READ_TOKEN",raising=False); assert main(["apply-command",str(request),"--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="no_change"; assert result["changed_entities"]==[]
def test_doctor_json_has_status_and_checks(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); monkeypatch.chdir(root); assert main(["doctor","--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="ok"; assert result["checks"]; assert all("code" in check and "ok" in check for check in result["checks"])
def test_recommend_context_json_is_stable(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_write_json(root/"recommend.json",{"schema_version":1,"operation":"recommend_context","target":"couple","only_unwatched":True,"runtime_max":120,"limit":4}); monkeypatch.chdir(root); assert main(["recommend-context","--request",str(request),"--format","json"])==0; first=capsys.readouterr().out; assert main(["recommend-context","--request",str(request),"--format","json"])==0; second=capsys.readouterr().out; assert first==second; parsed=json.loads(first); assert parsed["target"]=="couple"; assert len(parsed["candidates"])<=4

def test_assess_candidate_cli_returns_read_only_context(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_write_json(root/"assess.json",{"schema_version":1,"operation":"assess_candidate","target":"primary","candidate":{"id":"unwatched-fit-2020"},"text":"Зайдёт?"}); before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}; monkeypatch.chdir(root); assert main(["assess-candidate","--request",str(request),"--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["target"]=="primary"; assert result["candidate"]["id"]=="unwatched-fit-2020"; after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}; assert after==before

def test_assess_candidate_request_cannot_be_applied(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_write_json(root/"assess.json",{"schema_version":1,"operation":"assess_candidate","target":"primary","candidate":{"id":"unwatched-fit-2020"}}); monkeypatch.chdir(root); assert main(["apply-command",str(request),"--format","json"])==2; result=json.loads(capsys.readouterr().out); assert result["reason"]=="CommandValidationError"; assert "read-only" in result["message"]

def test_web_export_writes_manifest_and_reports_size(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); output=root/"build"/"manifest.json"; monkeypatch.chdir(root); assert main(["web-export","--output",str(output),"--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="ok"; assert result["output"]==str(output); assert result["works"]==8; assert result["bytes"]==output.stat().st_size; manifest=json.loads(output.read_text(encoding="utf-8")); assert manifest["schema_version"]==4


def test_refresh_work_metadata_cli_dry_run_initializes_provider(tmp_path, monkeypatch, capsys):
    import hashlib

    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media")
    work=root/"media/data/works/arrival-2016.yaml"
    digest="sha256:"+hashlib.sha256(work.read_bytes()).hexdigest()
    request=_write_json(root/"refresh-one.json",{
        "schema_version":1,
        "operation_id":"123e4567-e89b-42d3-a456-426614174203",
        "operation":"refresh_work_metadata",
        "work_ref":{"id":"arrival-2016"},
        "expected_work_digest":digest,
    })
    class Provider:
        def __init__(self, token): pass
        def fetch_work(self, media_type, provider_id):
            from media.providers.base import CanonicalMetadata
            return CanonicalMetadata(
                identity={"format":"movie","title_original":"Arrival","title_ru":"Прибытие","year":2016,"release_date":"2016-11-10","external_ids":{"tmdb":{"media_type":"movie","id":329865},"imdb":"tt2543164"}},
                external={"runtime_min":116,"provenance":{"provider":"tmdb","provider_id":329865,"fetched_at":"2026-10-07T00:00:00Z"}},
            )
        def search_work(self, title, year=None): return []
        def find_by_imdb(self, imdb_id): return []
    monkeypatch.chdir(root); monkeypatch.setenv("TMDB_READ_TOKEN","token"); monkeypatch.setattr("media.cli.TMDBProvider",Provider)
    assert main(["apply-command",str(request),"--dry-run","--format","json"])==0
    result=json.loads(capsys.readouterr().out)
    assert result["status"] in {"planned","no_change"}
    assert result["operation"]=="refresh_work_metadata"


def test_record_media_entry_existing_work_cli_needs_no_tmdb_token(tmp_path, monkeypatch, capsys):
    from media.domain.digests import compute_viewer_digest
    from media.tools.common import load_yaml

    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media")
    work=load_yaml(root/"media/data/works/arrival-2016.yaml")
    request=_write_json(root/"entry.json",{
        "schema_version":1,
        "operation_id":"123e4567-e89b-42d3-a456-426614174301",
        "idempotency_key":"123e4567-e89b-42d3-a456-426614174399",
        "operation":"record_media_entry",
        "work_ref":{"id":"arrival-2016"},
        "create_if_missing":False,
        "target_updates":[{"target":"primary","rating":{"score":9.0,"source":"explicit","confidence":"exact"}}],
        "preconditions":{"expected_viewer_digests":{"primary":compute_viewer_digest(work,"primary")}},
    })
    monkeypatch.chdir(root); monkeypatch.delenv("TMDB_READ_TOKEN",raising=False)
    assert main(["apply-command",str(request),"--dry-run","--format","json"])==0
    result=json.loads(capsys.readouterr().out)
    assert result["operation"]=="record_media_entry"
    assert result["status"] in {"planned","no_change"}


def test_record_media_entry_new_work_cli_initializes_provider(tmp_path, monkeypatch, capsys):
    from media.providers.base import CanonicalMetadata

    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media")
    metadata=CanonicalMetadata(
        identity={
            "format":"movie",
            "title_original":"New Film",
            "title_ru":"Новый фильм",
            "year":2024,
            "release_date":"2024-05-10",
            "external_ids":{"tmdb":{"media_type":"movie","id":987654},"imdb":"tt9876543"},
        },
        external={
            "genres":["genre.drama"],
            "runtime_min":121,
            "original_language":"en",
            "synopsis_short":"A carefully verified new film.",
            "provenance":{"provider":"tmdb","provider_id":987654,"fetched_at":"2026-10-07T00:00:00Z"},
        },
    )
    request=_write_json(root/"entry-new.json",{
        "schema_version":1,
        "operation_id":"123e4567-e89b-42d3-a456-426614174302",
        "idempotency_key":"123e4567-e89b-42d3-a456-426614174398",
        "operation":"record_media_entry",
        "work_ref":{"tmdb_media_type":"movie","tmdb_id":987654,"title":"New Film","year":2024},
        "create_if_missing":True,
        "target_updates":[{"target":"primary","viewing":{"status":"watched"}}],
        "creation_context":{
            "provider_identity":{"media_type":"movie","id":987654},
        },
        "semantic_snapshot":{
            "traits":[{"term":"story.intrigue","source":"llm_inferred","confidence":"high"}],
        },
        "preconditions":{"expected_viewer_digests":{}},
    })

    class Provider:
        def __init__(self, token): assert token=="token"
        def fetch_work(self, media_type, provider_id):
            assert (media_type,provider_id)==("movie",987654)
            return metadata
        def search_work(self, *args, **kwargs): raise AssertionError("stable identity must not search")
        def find_by_imdb(self, *args, **kwargs): raise AssertionError("stable identity must not search")

    monkeypatch.chdir(root); monkeypatch.setenv("TMDB_READ_TOKEN","token"); monkeypatch.setattr("media.cli.TMDBProvider",Provider)
    assert main(["apply-command",str(request),"--dry-run","--format","json"])==0
    result=json.loads(capsys.readouterr().out)
    assert result["operation"]=="record_media_entry"
    assert result["status"]=="planned"


def test_media_entry_context_cli_returns_compact_json(tmp_path, monkeypatch, capsys):
    root=copy_fixture_repo(tmp_path)
    request=_write_json(root/"entry-context.json",{
        "schema_version":1,
        "operation":"media_entry_context",
        "work_ref":{"id":"arrival-2016"},
        "target":"primary",
    })
    monkeypatch.chdir(root)
    assert main(["media-entry-context","--request",str(request),"--format","json"])==0
    result=json.loads(capsys.readouterr().out)
    assert result["exists"] is True
    assert result["target"]=="primary"
    assert "history" not in result["viewer"]["state"]
    assert len(json.dumps(result,ensure_ascii=False,separators=(",",":")).encode("utf-8")) < 6000
