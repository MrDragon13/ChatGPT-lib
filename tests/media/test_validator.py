from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import yaml

from media.repository.yaml_repo import YamlRepository
from media.tools.common import dump_yaml, write_jsonl
from media.tools.validate import validate_repository


def seed_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for sub in ["works", "collections", "lists", "interactions", "tombstones"]:
        (root / f"media/data/{sub}").mkdir(parents=True, exist_ok=True)
    (root / "media/preferences/explicit").mkdir(parents=True)
    shutil.copytree(Path("media/schemas"), root / "media/schemas")
    shutil.copytree(Path("media/config"), root / "media/config")
    shutil.copy(Path("media/vocabulary.yaml"), root / "media/vocabulary.yaml")
    shutil.copy(Path("media/preferences/explicit/primary.yaml"), root / "media/preferences/explicit/primary.yaml")
    dump_yaml(root / "media/data/works/movie-a-2020.yaml", {"schema_version":4,"id":"movie-a-2020","entity_type":"work","identity":{"format":"movie","title_original":"Movie A","title_ru":"Фильм A","year":2020},"viewer_signals":{"partner":{"reaction":{"value":"liked","source":"explicit","confidence":"high"}}}})
    dump_yaml(root / "media/data/works/series-a-2021.yaml", {"schema_version":4,"id":"series-a-2021","entity_type":"work","identity":{"format":"series","title_original":"Series A","title_ru":"Сериал A","year":2021}})
    return root


def codes(root: Path) -> list[str]:
    return [i.code for i in validate_repository(root)]


def test_minimal_valid_repo_has_no_generated_dependency(tmp_path: Path):
    assert validate_repository(seed_repo(tmp_path)) == []


def test_duplicate_imdb_fails(tmp_path: Path):
    root = seed_repo(tmp_path)
    for name in ["movie-a-2020", "series-a-2021"]:
        p = root / f"media/data/works/{name}.yaml"; doc = yaml.safe_load(p.read_text()); doc["identity"]["external_ids"]={"imdb":"tt1234567"}; dump_yaml(p, doc)
    assert "duplicate_imdb" in codes(root)


def test_tmdb_composite_uniqueness_allows_movie_tv_collision(tmp_path: Path):
    root = seed_repo(tmp_path)
    a=root/"media/data/works/movie-a-2020.yaml"; b=root/"media/data/works/series-a-2021.yaml"
    da=yaml.safe_load(a.read_text()); db=yaml.safe_load(b.read_text()); da["identity"]["external_ids"]={"tmdb":{"media_type":"movie","id":123}}; db["identity"]["external_ids"]={"tmdb":{"media_type":"tv","id":123}}; dump_yaml(a,da); dump_yaml(b,db)
    assert "duplicate_tmdb" not in codes(root)
    dump_yaml(root/"media/data/works/movie-b-2022.yaml", {"schema_version":4,"id":"movie-b-2022","entity_type":"work","identity":{"format":"movie","title_original":"B","title_ru":"Б","year":2022,"external_ids":{"tmdb":{"media_type":"movie","id":123}}}})
    assert "duplicate_tmdb" in codes(root)


def test_missing_and_self_relations_fail(tmp_path: Path):
    root=seed_repo(tmp_path); p=root/"media/data/works/movie-a-2020.yaml"; d=yaml.safe_load(p.read_text()); d["canonical_relations"]=[{"target_id":"missing","type":"sequel"},{"target_id":"movie-a-2020","type":"remake"}]; dump_yaml(p,d); c=codes(root); assert "missing_ref" in c and "self_relation" in c


def test_tombstone_cycle_and_stale_reference_fail(tmp_path: Path):
    root=seed_repo(tmp_path); dump_yaml(root/"media/data/tombstones/old-a.yaml", {"schema_version":4,"id":"old-a","entity_type":"tombstone","status":"merged","redirect_to":"old-b"}); dump_yaml(root/"media/data/tombstones/old-b.yaml", {"schema_version":4,"id":"old-b","entity_type":"tombstone","status":"merged","redirect_to":"old-a"}); dump_yaml(root/"media/data/lists/x.yaml", {"schema_version":4,"id":"x","entity_type":"list","target":"primary","title":"X","member_ids":["old-a"]}); c=codes(root); assert "redirect_cycle" in c and "stale_ref" in c


def test_invalid_group_member_fails(tmp_path: Path):
    root=seed_repo(tmp_path); dump_yaml(root/"media/config/groups.yaml", {"schema_version":4,"groups":{"couple":{"members":["primary","ghost"]}}}); assert "missing_viewer" in codes(root)


def test_alias_unknown_term_and_duplicate_season_fail_but_season_zero_is_valid(tmp_path: Path):
    root=seed_repo(tmp_path); p=root/"media/data/works/series-a-2021.yaml"; d=yaml.safe_load(p.read_text()); d["seasons"]=[{"number":0},{"number":1},{"number":1}]; d["viewer_signals"]={"primary":{"feedback":{"signals":[{"term":"time_loop","sentiment":"positive","strength":2,"source":"inferred","confidence":"medium"},{"term":"unknown.term","sentiment":"positive","strength":1,"source":"inferred","confidence":"low"}]}}}; dump_yaml(p,d); c=codes(root); assert "duplicate_season" in c and "vocabulary_alias" in c and "vocabulary_unknown" in c


def test_interaction_filename_month_timestamp_and_references(tmp_path: Path):
    root=seed_repo(tmp_path); event={"schema_version":4,"id":"evt-1","entity_type":"interaction","at":"2026-11-01T20:00:00+02:00","target":"couple","type":"recommended","work_id":"movie-a-2020"}; write_jsonl(root/"media/data/interactions/2026-10.jsonl", [event]); assert "interaction_month" in codes(root); bad={**event,"id":"evt-2","at":"2026-10-01T20:00:00+02:00","work_id":"missing","target":"ghost"}; write_jsonl(root/"media/data/interactions/not-a-month.jsonl", [bad]); c=codes(root); assert "interaction_filename" in c and "missing_ref" in c and "missing_target" in c


