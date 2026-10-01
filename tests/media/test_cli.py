from __future__ import annotations

import json
from pathlib import Path

from media.cli import main
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo

UUID="123e4567-e89b-42d3-a456-426614174201"

def _write_json(path:Path,data:dict)->Path: path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8"); return path
def _feedback_command(path:Path)->Path: return _write_json(path,{"schema_version":1,"operation_id":UUID,"operation":"record_viewing_feedback","work_ref":{"id":"arrival-2016"},"target_updates":[{"target":"primary","rating":{"score":8.5,"source":"explicit_approx","confidence":"high"}}]})
def test_apply_command_dry_run_changes_nothing(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_feedback_command(root/"request.json"); before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}; monkeypatch.chdir(root); assert main(["apply-command",str(request),"--dry-run","--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="planned"; after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}; assert after==before
def test_apply_command_json_reports_status_entities_and_files(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_feedback_command(root/"request.json"); monkeypatch.chdir(root); assert main(["apply-command",str(request),"--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="applied"; assert result["changed_entities"]==["arrival-2016"]; assert "media/data/works/arrival-2016.yaml" in result["changed_files"]; assert any(path.startswith(".media/operations/") for path in result["changed_files"])
def test_add_existing_work_reports_no_change_without_tmdb_token(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_write_json(root/"add.json",{"schema_version":1,"operation_id":"123e4567-e89b-42d3-a456-426614174202","operation":"add_work","work_ref":{"title":"Arrival","year":2016}}); monkeypatch.chdir(root); monkeypatch.delenv("TMDB_READ_TOKEN",raising=False); assert main(["apply-command",str(request),"--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="no_change"; assert result["changed_entities"]==[]
def test_doctor_json_has_status_and_checks(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); monkeypatch.chdir(root); assert main(["doctor","--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="ok"; assert result["checks"]; assert all("code" in check and "ok" in check for check in result["checks"])
def test_recommend_context_json_is_stable(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); request=_write_json(root/"recommend.json",{"schema_version":1,"operation":"recommend_context","target":"couple","only_unwatched":True,"runtime_max":120,"limit":4}); monkeypatch.chdir(root); assert main(["recommend-context","--request",str(request),"--format","json"])==0; first=capsys.readouterr().out; assert main(["recommend-context","--request",str(request),"--format","json"])==0; second=capsys.readouterr().out; assert first==second; parsed=json.loads(first); assert parsed["target"]=="couple"; assert len(parsed["candidates"])<=4

def test_web_export_writes_manifest_and_reports_size(tmp_path,monkeypatch,capsys):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media"); output=root/"build"/"manifest.json"; monkeypatch.chdir(root); assert main(["web-export","--output",str(output),"--format","json"])==0; result=json.loads(capsys.readouterr().out); assert result["status"]=="ok"; assert result["output"]==str(output); assert result["works"]==8; assert result["bytes"]==output.stat().st_size; manifest=json.loads(output.read_text(encoding="utf-8")); assert manifest["schema_version"]==1
