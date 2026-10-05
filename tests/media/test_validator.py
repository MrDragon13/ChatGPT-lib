from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import yaml

from media.repository.yaml_repo import YamlRepository
from media.service.reassessment import PILOT_ID, build_initial_ledger, ledger_bytes
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


def write_valid_pilot_ledger(root: Path) -> tuple[Path, dict]:
    work_path = root / "media/data/works/movie-a-2020.yaml"
    work_doc = yaml.safe_load(work_path.read_text(encoding="utf-8"))
    work_doc.setdefault("viewer_signals", {})["primary"] = {
        "viewing": {"status": "watched"},
        "rating": {"score": 8.0, "source": "explicit", "confidence": "exact"},
    }
    dump_yaml(work_path, work_doc)
    ledger = build_initial_ledger(
        YamlRepository(root / "media"),
        pilot_id=PILOT_ID,
        base_revision="35afaca898eae6937066f230906b41af0e1f6690",
        baseline_path="media/baselines/intelligence-stage-a.json",
        baseline_document={"schema_version": 2, "canonical_input_digest": "sha256:" + "9" * 64},
    )
    path = root / "media/pilots/legacy-reassessment-primary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ledger_bytes(ledger))
    return path, ledger


def write_ledger(path: Path, document: dict) -> None:
    path.write_bytes(ledger_bytes(document))


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


def test_reassessment_ledger_is_optional_but_malformed_snapshot_is_rejected(tmp_path: Path):
    root = seed_repo(tmp_path)
    assert "schema" not in codes(root)
    path, _ = write_valid_pilot_ledger(root)
    assert validate_repository(root) == []
    path.write_text("{}\n", encoding="utf-8")
    assert "schema" in codes(root)


def test_reassessment_snapshot_rejects_unknown_work_and_inconsistent_frozen_order(tmp_path: Path):
    root = seed_repo(tmp_path)
    path, ledger = write_valid_pilot_ledger(root)
    broken = deepcopy(ledger)
    original = broken["frozen_cohort"]["work_ids"][0]
    item = broken["frozen_cohort"]["items"].pop(original)
    lifecycle = broken["items"].pop(original)
    broken["frozen_cohort"]["work_ids"] = ["ghost-work"]
    broken["frozen_cohort"]["items"]["ghost-work"] = item
    broken["items"]["ghost-work"] = lifecycle
    write_ledger(path, broken)
    assert "reassessment_missing_work" in codes(root)

    broken = deepcopy(ledger)
    work_id = broken["frozen_cohort"]["work_ids"][0]
    broken["frozen_cohort"]["items"][work_id]["order_rank"] = 5
    write_ledger(path, broken)
    assert "reassessment_order" in codes(root)


def test_reassessment_snapshot_requires_review_provenance_and_completed_main_pass(tmp_path: Path):
    root = seed_repo(tmp_path)
    path, ledger = write_valid_pilot_ledger(root)
    work_id = ledger["frozen_cohort"]["work_ids"][0]

    broken = deepcopy(ledger)
    broken["items"][work_id] = {"status": "reviewed", "outcome": "changed"}
    write_ledger(path, broken)
    assert "reassessment_reviewed_provenance" in codes(root)

    broken = deepcopy(ledger)
    broken["pilot_status"] = "completed"
    write_ledger(path, broken)
    assert "reassessment_incomplete_pilot" in codes(root)


def test_reassessment_closed_session_cannot_retain_in_progress_item(tmp_path: Path):
    root = seed_repo(tmp_path)
    path, ledger = write_valid_pilot_ledger(root)
    work_id = ledger["frozen_cohort"]["work_ids"][0]
    session_id = "123e4567-e89b-42d3-a456-426614174001"
    ledger["items"][work_id] = {
        "status": "in_progress",
        "session_id": session_id,
        "reserved_at": "2026-10-05T12:00:00+00:00",
        "pre_review_feedback_digest": "sha256:" + "1" * 64,
        "pre_review_work_file_digest": "sha256:" + "2" * 64,
    }
    ledger["sessions"] = [{
        "session_id": session_id,
        "reserved_work_ids": [work_id],
        "status": "closed",
        "opened_at": "2026-10-05T12:00:00+00:00",
        "closed_at": "2026-10-05T12:10:00+00:00",
    }]
    write_ledger(path, ledger)
    assert "reassessment_closed_session_in_progress" in codes(root)


def test_reassessment_closed_session_counters_are_monotonic_but_may_lag_current_total(tmp_path: Path):
    root = seed_repo(tmp_path)
    path, ledger = write_valid_pilot_ledger(root)
    session_a = {
        "session_id": "123e4567-e89b-42d3-a456-426614174001",
        "reserved_work_ids": [ledger["frozen_cohort"]["work_ids"][0]],
        "status": "closed",
        "opened_at": "2026-10-05T12:00:00+00:00",
        "closed_at": "2026-10-05T12:10:00+00:00",
        "snapshot": {"reviewed_total": 2, "deferred_total": 1},
    }
    session_b = {
        "session_id": "123e4567-e89b-42d3-a456-426614174002",
        "reserved_work_ids": [ledger["frozen_cohort"]["work_ids"][0]],
        "status": "closed",
        "opened_at": "2026-10-05T13:00:00+00:00",
        "closed_at": "2026-10-05T13:10:00+00:00",
        "snapshot": {"reviewed_total": 1, "deferred_total": 1},
    }
    ledger["sessions"] = [session_a, session_b]
    write_ledger(path, ledger)
    assert "reassessment_nonmonotonic_session" in codes(root)

    ledger["sessions"] = [session_a]
    write_ledger(path, ledger)
    assert "reassessment_nonmonotonic_session" not in codes(root)


def test_reassessment_validation_does_not_compare_current_feedback_to_frozen_snapshot(tmp_path: Path):
    root = seed_repo(tmp_path)
    _, ledger = write_valid_pilot_ledger(root)
    work_path = root / "media/data/works/movie-a-2020.yaml"
    work_doc = yaml.safe_load(work_path.read_text(encoding="utf-8"))
    work_doc["viewer_signals"]["primary"]["viewing"] = {"status": "unwatched"}
    work_doc["viewer_signals"]["primary"].pop("rating", None)
    dump_yaml(work_path, work_doc)
    assert ledger["frozen_cohort"]["items"]["movie-a-2020"]["viewing_status"] == "watched"
    assert validate_repository(root) == []
