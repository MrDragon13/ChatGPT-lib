from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from media.domain.commands import AssessCandidateRequest, MediaEntryContextRequest, RecommendContextRequest, TasteContextRequest
from media.domain.types import WorkRef
from media.service.assessment import build_candidate_assessment_context
from media.service.media_entry_context import build_media_entry_context
from media.service.recommend import build_recommend_context
from media.service.taste_context import build_taste_context
from media.service.web_export import build_web_manifest
from media.tools.archive_library import write_library_archive
from media.tools.build_profiles import build_profile
from media.tools.common import dump_yaml, load_yaml
from media.tools.doctor import doctor
from media.tools.migrate_v6_reset import ResetSafetyError, apply_v6_reset, plan_v6_reset
from media.tools.validate import validate_repository
from tests.media.fixture_repo import copy_fixture_repo


def _prepare_reset_repo(tmp_path: Path) -> tuple[Path, Path]:
    root=copy_fixture_repo(tmp_path)

    explicit=root/"media/preferences/explicit/primary.yaml"
    dump_yaml(explicit,{
        "schema_version":4,
        "target":"primary",
        "preferences":[{
            "id":"execution-over-genre",
            "statement":"Качество реализации важнее жанра.",
            "source":"explicit",
            "confidence":"exact",
        }],
        "rules":[{
            "id":"slow-pacing-context",
            "statement":"Медленный темп допустим, если оправдан историей.",
            "source":"explicit",
            "confidence":"exact",
        }],
        "constraints":[],
    })
    dump_yaml(root/"media/preferences/inferred/primary.yaml",{
        "schema_version":1,
        "target":"primary",
        "hypotheses":[{
            "id":"legacy-hypothesis",
            "statement":"Старая гипотеза",
            "confidence":"medium",
            "evidence":[],
        }],
    })
    dump_yaml(root/"media/data/collections/legacy.yaml",{
        "schema_version":4,
        "id":"legacy-collection",
        "entity_type":"collection",
        "name_ru":"Старая подборка",
        "name_original":"Legacy Collection",
        "member_ids":[],
    })
    dump_yaml(root/"media/data/relations/similarity/primary.yaml",{
        "schema_version":1,
        "target":"primary",
        "relations":[],
    })
    interactions=root/"media/data/interactions/2026-10.jsonl"
    interactions.parent.mkdir(parents=True,exist_ok=True)
    interactions.write_text(json.dumps({
        "schema_version":4,
        "id":"evt-reset",
        "entity_type":"interaction",
        "at":"2026-10-07T10:00:00Z",
        "target":"primary",
        "type":"selected",
        "work_id":"arrival-2016",
    })+"\n",encoding="utf-8")

    pilot=root/"media/pilots/legacy-reassessment-primary.json"
    pilot.parent.mkdir(parents=True,exist_ok=True)
    pilot.write_text("{}\n",encoding="utf-8")

    baselines=root/"media/baselines"
    baselines.mkdir(parents=True,exist_ok=True)
    (baselines/"intelligence-stage-a.json").write_text("{}\n",encoding="utf-8")
    (baselines/"intelligence-stage-a.meta.json").write_text("{}\n",encoding="utf-8")

    operations=root/".media/operations"
    operations.mkdir(parents=True,exist_ok=True)
    (operations/"old.json").write_text("{}\n",encoding="utf-8")

    archive=root/"docs/archive/media-library-before-v6-reset-2026-10-07.md"
    write_library_archive(root,archive)
    return root,archive


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)):path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_quality_fixture_catalog_preserves_only_required_behavioral_cases():
    path=Path("tests/media/fixtures/v6_quality/cases.yaml")
    doc=yaml.safe_load(path.read_text(encoding="utf-8"))
    ids={item["id"] for item in doc["cases"]}
    assert ids=={
        "positive-intrigue-problem-solving",
        "mixed-evidence",
        "couple-disagreement",
        "sparse-semantics",
        "explicit-similarity-not-preference",
        "stale-inferred-fresh-explicit",
    }
    raw=path.read_text(encoding="utf-8")
    assert "arrival-2016" not in raw
    assert "source-code-2011" not in raw
    assert "tmdb" not in raw.lower()


def test_reset_plan_is_read_only_and_lists_only_cutover_state(tmp_path):
    root,archive=_prepare_reset_repo(tmp_path)
    before=_snapshot(root)

    plan=plan_v6_reset(root,archive)

    assert _snapshot(root)==before
    assert "media/data/works/arrival-2016.yaml" in plan.remove_paths
    assert "media/preferences/inferred/primary.yaml" in plan.remove_paths
    assert "media/pilots/legacy-reassessment-primary.json" in plan.remove_paths
    assert ".media/operations/old.json" in plan.remove_paths
    assert "media/preferences/explicit/primary.yaml" in plan.preserve_paths
    assert "media/vocabulary.yaml" in plan.preserve_paths


def test_reset_refuses_corrupt_archive_before_any_mutation(tmp_path):
    root,archive=_prepare_reset_repo(tmp_path)
    archive.write_text(archive.read_text(encoding="utf-8")+"\ncorrupt\n",encoding="utf-8")
    before=_snapshot(root)

    with pytest.raises(ResetSafetyError,match="archive"):
        apply_v6_reset(root,archive)

    assert _snapshot(root)==before


def test_reset_refuses_pending_request_before_any_mutation(tmp_path):
    root,archive=_prepare_reset_repo(tmp_path)
    pending=root/".media/requests/pending.json"
    pending.parent.mkdir(parents=True,exist_ok=True)
    pending.write_text("{}\n",encoding="utf-8")
    before=_snapshot(root)

    with pytest.raises(ResetSafetyError,match="pending"):
        apply_v6_reset(root,archive)

    assert _snapshot(root)==before


def test_successful_reset_clears_active_v5_state_and_preserves_explicit_rules(tmp_path):
    root,archive=_prepare_reset_repo(tmp_path)
    explicit_before=(root/"media/preferences/explicit/primary.yaml").read_bytes()
    vocabulary_before=(root/"media/vocabulary.yaml").read_bytes()

    plan=apply_v6_reset(root,archive)

    assert plan.remove_paths
    assert list((root/"media/data/works").glob("*.yaml"))==[]
    assert list((root/"media/data/collections").glob("*.yaml"))==[]
    assert list((root/"media/data/relations/similarity").glob("*.yaml"))==[]
    assert list((root/"media/data/interactions").glob("*.jsonl"))==[]
    assert list((root/"media/preferences/inferred").glob("*.yaml"))==[]
    assert not (root/"media/pilots/legacy-reassessment-primary.json").exists()
    assert list((root/"media/baselines").glob("intelligence-stage-a*.json"))==[]
    assert list((root/".media/operations").glob("*.json"))==[]

    assert (root/"media/preferences/explicit/primary.yaml").read_bytes()==explicit_before
    assert (root/"media/vocabulary.yaml").read_bytes()==vocabulary_before
    assert (root/"media/generated/index.jsonl").read_bytes()==b""

    primary=load_yaml(root/"media/generated/profiles/primary.yaml")
    partner=load_yaml(root/"media/generated/profiles/partner.yaml")
    couple=load_yaml(root/"media/generated/profiles/couple.yaml")
    assert primary["evidence"]["entity_count"]==0
    assert partner["evidence"]["entity_count"]==0
    assert couple["evidence"]["entity_count"]==0
    assert primary["explicit_preferences"][0]["id"]=="execution-over-genre"
    assert "inferred_preferences" not in primary


def test_empty_library_tooling_and_read_contexts_are_deterministic(tmp_path):
    root,archive=_prepare_reset_repo(tmp_path)
    apply_v6_reset(root,archive)
    media=root/"media"

    first_index=(media/"generated/index.jsonl").read_bytes()
    first_profiles={
        path.name:path.read_bytes()
        for path in sorted((media/"generated/profiles").glob("*.yaml"))
    }

    assert validate_repository(root)==[]
    assert doctor(root).ok is True

    manifest_first=build_web_manifest(media)
    manifest_second=build_web_manifest(media)
    assert manifest_first==manifest_second
    assert manifest_first["works"]==[]
    assert all(context["candidates"]==[] for context in manifest_first["recommendations"].values())

    missing=build_media_entry_context(media,MediaEntryContextRequest(
        schema_version=1,
        work_ref=WorkRef(title="Новый фильм",year=2026),
        target="primary",
    ))
    assert missing["exists"] is False

    taste=build_taste_context(media,TasteContextRequest(
        schema_version=1,target="primary",recent_limit=10,representative_limit=10,
    ))
    assert taste["representative"]=={"high":[],"low":[]}
    assert taste["recent_feedback"]==[]
    assert taste["profile"]["explicit_preferences"][0]["id"]=="execution-over-genre"
    assert "cold_start_no_work_evidence" in taste["limitations"]

    recommend=build_recommend_context(media,RecommendContextRequest(
        schema_version=1,
        target="primary",
        text="Что посмотреть?",
        only_unwatched=True,
        runtime_max=None,
        include_not_interested=False,
        limit=10,
    ))
    assert recommend["candidates"]==[]
    assert recommend["coverage"]["pool_total"]==0
    assert "empty_library" in recommend["limitations"]

    assessment=build_candidate_assessment_context(media,AssessCandidateRequest(
        schema_version=1,
        target="primary",
        candidate=WorkRef(title="Внешний кандидат",year=2026),
        text="Мне зайдёт?",
    ))
    assert assessment["candidate"]["kind"]=="external"
    assert assessment["taste_context"]["representative"]=={"high":[],"low":[]}
    assert "cold_start_no_work_evidence" in assessment["taste_context"]["limitations"]

    # Re-running the reset-generated builders must be byte-stable.
    from media.tools.rebuild import rebuild_generated
    rebuild_generated(media)
    assert (media/"generated/index.jsonl").read_bytes()==first_index
    assert {
        path.name:path.read_bytes()
        for path in sorted((media/"generated/profiles").glob("*.yaml"))
    }==first_profiles
