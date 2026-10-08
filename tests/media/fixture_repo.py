from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import yaml

from media.tools.build_index import write_index


def copy_fixture_repo(tmp_path: Path) -> Path:
    src=Path(__file__).parents[1]/"fixtures"/"media_repo"; dst=tmp_path/"repo"; shutil.copytree(src,dst); project_media=Path(__file__).parents[2]/"media"
    if (project_media/"schemas").exists(): shutil.copytree(project_media/"schemas",dst/"media"/"schemas",dirs_exist_ok=True)
    if (project_media/"config"/"intelligence.yaml").exists():
        (dst/"media"/"config").mkdir(parents=True,exist_ok=True)
        shutil.copy2(project_media/"config"/"intelligence.yaml",dst/"media"/"config"/"intelligence.yaml")
    if (project_media/"vocabulary.yaml").exists(): shutil.copy2(project_media/"vocabulary.yaml",dst/"media"/"vocabulary.yaml")
    return dst


def prepare_derived(repo_root: Path) -> None:
    media=repo_root/"media"; write_index(media); profiles=media/"generated"/"profiles"; profiles.mkdir(parents=True,exist_ok=True); primary={"schema_version":4,"target":"primary","generated_from":"test-fixture","affinities":{"story.intrigue":{"score":1.0,"confidence":"high","evidence_count":1,"evidence":[]},"reaction.pacing_dragging":{"score":-1.0,"confidence":"medium","evidence_count":1,"evidence":[]}},"explicit_preferences":[],"rules":[],"constraints":[],"summary":{},"evidence":{"entity_count":8}}; couple={**primary,"target":"couple"}; (profiles/"primary.yaml").write_text(yaml.safe_dump(primary,sort_keys=False,allow_unicode=True),encoding="utf-8"); (profiles/"couple.yaml").write_text(yaml.safe_dump(couple,sort_keys=False,allow_unicode=True),encoding="utf-8"); db=media/"generated"/"database.sqlite"; con=sqlite3.connect(db)
    try:
        con.execute("CREATE TABLE works (id TEXT PRIMARY KEY, title_original TEXT, title_ru TEXT, alternate_titles_json TEXT, year INTEGER, runtime_min INTEGER)")
        for line in (media/"generated/index.jsonl").read_text(encoding="utf-8").splitlines():
            row=json.loads(line); con.execute("INSERT INTO works VALUES (?,?,?,?,?,?)",(row["id"],row["title_original"],row["title_ru"],json.dumps(row["alternate_titles"],ensure_ascii=False),row["year"],row["runtime_min"]))
        con.commit()
    finally: con.close()


def append_material_rating_event(
    repo_root: Path,
    *,
    target: str = "primary",
    work_id: str = "arrival-2016",
    score: float = 8.0,
    event_id: str = "123e4567-e89b-42d3-a456-426614174500",
    at: str = "2026-10-07T12:00:00Z",
) -> None:
    path=repo_root/f"media/data/works/{work_id}.yaml"
    doc=yaml.safe_load(path.read_text(encoding="utf-8"))
    signal=doc.setdefault("viewer_signals",{}).setdefault(target,{})
    previous={}
    if "rating" in signal:
        previous["rating"]=dict(signal["rating"])
    rating={"score":score,"source":"explicit","confidence":"exact"}
    signal["rating"]=rating
    signal.setdefault("history",[]).append({
        "at":at,
        "event_id":event_id,
        "material_evidence":True,
        "previous":previous,
        "current":{"rating":dict(rating)},
    })
    path.write_text(yaml.safe_dump(doc,sort_keys=False,allow_unicode=True),encoding="utf-8")
