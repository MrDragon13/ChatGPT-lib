from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any

from media.tools.common import dump_yaml, load_yaml
from tests.media.fixture_repo import append_material_rating_event, copy_fixture_repo, prepare_derived


def _web_export_module():
    assert importlib.util.find_spec("media.service.web_export") is not None, "web export module is not implemented yet"
    return importlib.import_module("media.service.web_export")


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _all_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        keys = [str(key) for key in value]
        for child in value.values():
            keys.extend(_all_keys(child))
        return keys
    if isinstance(value, list):
        keys: list[str] = []
        for child in value:
            keys.extend(_all_keys(child))
        return keys
    return []


def _write_similarity(root: Path, relations: list[dict[str, Any]], target: str = "primary") -> None:
    path = root / "media/data/relations/similarity" / f"{target}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    dump_yaml(path, {"schema_version": 1, "target": target, "relations": relations})


def _similarity(left: dict[str, Any], right: dict[str, Any], note: str = "Оба держат интригой") -> dict[str, Any]:
    return {
        "type": "similar",
        "left": left,
        "right": right,
        "terms": ["story.intrigue"],
        "note": note,
        "updated_at": "2026-10-03T20:00:00+00:00",
        "provenance": {"source": "explicit"},
    }


def test_manifest_uses_configured_targets_vocabulary_and_canonical_signals(tmp_path):
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    module = _web_export_module()

    manifest = module.build_web_manifest(root / "media")

    assert manifest["schema_version"] == 3
    assert manifest["default_target"] == "primary"
    assert manifest["targets"] == {
        "viewers": ["partner", "primary"],
        "groups": {"couple": ["primary", "partner"]},
    }
    assert manifest["vocabulary"]["story.intrigue"]["label_ru"] == "Интрига"

    works = {work["id"]: work for work in manifest["works"]}
    arrival = works["arrival-2016"]
    assert arrival["identity"]["title_ru"] == "Прибытие"
    assert arrival["viewer_signals"]["primary"]["viewing"]["status"] == "watched"
    assert arrival["viewer_signals"]["partner"]["viewing"]["status"] == "watched"
    assert set(arrival["similarities"]) == {"primary", "partner", "couple"}
    assert set(manifest["taste_contexts"]) == {"primary", "partner", "couple"}


def test_manifest_projects_one_canonical_similarity_symmetrically_to_both_work_pages(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _write_similarity(root, [_similarity(
        {"kind": "canonical", "work_id": "arrival-2016"},
        {"kind": "canonical", "work_id": "unwatched-fit-2020"},
    )])
    prepare_derived(root)
    manifest = _web_export_module().build_web_manifest(root / "media")
    works = {work["id"]: work for work in manifest["works"]}

    arrival = works["arrival-2016"]["similarities"]["primary"]
    puzzle = works["unwatched-fit-2020"]["similarities"]["primary"]
    assert len(arrival) == len(puzzle) == 1
    assert arrival[0]["other"] == {
        "kind": "canonical",
        "id": "unwatched-fit-2020",
        "title_original": "Puzzle Run",
        "title_ru": "Забег с загадкой",
        "year": 2020,
    }
    assert puzzle[0]["other"]["id"] == "arrival-2016"
    assert arrival[0]["terms"] == ["story.intrigue"]
    assert arrival[0]["provenance"] == {"source": "explicit"}


def test_manifest_projects_external_similarity_without_fabricating_local_work(tmp_path):
    root = copy_fixture_repo(tmp_path)
    external = {"kind": "external", "provider": "tmdb", "media_type": "movie", "id": 45612, "title": "Source Code", "year": 2011}
    _write_similarity(root, [_similarity(external, {"kind": "canonical", "work_id": "arrival-2016"})])
    prepare_derived(root)
    manifest = _web_export_module().build_web_manifest(root / "media")
    works = {work["id"]: work for work in manifest["works"]}

    assert works["arrival-2016"]["similarities"]["primary"][0]["other"] == external
    assert "source-code-2011" not in works


def test_manifest_exports_structured_semantic_fingerprint_and_keeps_compact_traits(tmp_path):
    root = copy_fixture_repo(tmp_path)
    work_path = root / "media/data/works/arrival-2016.yaml"
    work = load_yaml(work_path)
    work.setdefault("metadata", {}).setdefault("semantic", {})["traits"] = [
        {"term":"story.intrigue","source":"llm_inferred","confidence":"high"},
    ]
    dump_yaml(work_path, work)
    prepare_derived(root)
    module = _web_export_module()

    manifest = module.build_web_manifest(root / "media")
    arrival = {work["id"]: work for work in manifest["works"]}["arrival-2016"]

    assert arrival["traits"] == ["story.intrigue"]
    assert arrival["semantic_fingerprint"] == [
        {"term":"story.intrigue","source":"llm_inferred","confidence":"high"},
    ]


def test_manifest_exports_inferred_preferences_without_inventing_numeric_affinity(tmp_path):
    root = copy_fixture_repo(tmp_path)
    inferred = root / "media/preferences/inferred"
    inferred.mkdir(parents=True, exist_ok=True)
    dump_yaml(inferred / "primary.yaml", {
        "schema_version":1,
        "target":"primary",
        "updated_at":"2026-10-03T00:00:00Z",
        "hypotheses":[{
            "id":"intrigue-pattern",
            "statement":"Повторяется любовь к интриге.",
            "affinity":0.8,
            "confidence":"medium",
            "terms":["story.intrigue"],
            "evidence":[{"entity_id":"arrival-2016","kind":"rating_correlation"}],
        }],
    })
    prepare_derived(root)
    module = _web_export_module()

    manifest = module.build_web_manifest(root / "media")
    primary = manifest["taste_contexts"]["primary"]

    assert primary["target"] == "primary"
    assert primary["profile"]["inferred_preferences"][0]["id"] == "intrigue-pattern"
    assert primary["profile"]["strongest_affinities"] == []


def test_manifest_missing_intelligence_layers_are_explicitly_empty(tmp_path):
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    module = _web_export_module()

    manifest = module.build_web_manifest(root / "media")
    works = {work["id"]: work for work in manifest["works"]}
    sparse = works["hidden-name-2010"]

    assert sparse["identity"]["title_ru"] == "Секрет"
    assert sparse["metadata"]["external"] == {}
    assert sparse["viewer_signals"] == {}
    assert sparse["group_signals"] == {}
    assert sparse["semantic_fingerprint"] == []
    assert all(value == [] for value in sparse["similarities"].values())
    assert manifest["taste_contexts"]["partner"]["profile"]["inferred_preferences"] == []


def test_manifest_couple_context_preserves_agreement_disagreement_shape(tmp_path):
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    module = _web_export_module()

    manifest = module.build_web_manifest(root / "media")
    couple = manifest["taste_contexts"]["couple"]

    assert couple["couple"]["members"] == ["primary", "partner"]
    assert isinstance(couple["couple"]["agreements"], list)
    assert isinstance(couple["couple"]["disagreements"], list)


def test_recommendations_reuse_read_context_without_candidate_score(tmp_path):
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    module = _web_export_module()

    manifest = module.build_web_manifest(root / "media")

    assert set(manifest["recommendations"]) == {"primary", "partner", "couple"}
    for context in manifest["recommendations"].values():
        assert context["request"]["only_unwatched"] is True
        assert context["request"]["runtime_max"] is None
        assert context["request"]["include_not_interested"] is False
        assert all("score" not in candidate for candidate in context["candidates"])


def test_export_is_read_only_and_does_not_serialize_secret_keys(tmp_path):
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    module = _web_export_module()
    media_root = root / "media"
    before = _snapshot_tree(media_root)

    output = tmp_path / "manifest.json"
    result = module.write_web_manifest(media_root, output)

    assert result == output
    assert output.exists()
    assert _snapshot_tree(media_root) == before

    manifest = module.build_web_manifest(media_root)
    suspicious = ("token", "secret", "credential", "password")
    assert not [key for key in _all_keys(manifest) if any(part in key.lower() for part in suspicious)]

def test_manifest_v3_does_not_publish_v6_reanalysis_fields_before_cutover(tmp_path):
    root=copy_fixture_repo(tmp_path)
    for index in range(5):
        append_material_rating_event(
            root,
            score=7.0 + index / 2,
            event_id=f"123e4567-e89b-42d3-a456-4266141749{index:02d}",
            at=f"2026-10-07T16:0{index}:00Z",
        )
    prepare_derived(root)
    manifest=_web_export_module().build_web_manifest(root/"media")

    for context in manifest["taste_contexts"].values():
        assert "reanalysis" not in context
        assert "taste_reanalysis_due" not in (context.get("limitations") or [])
    for context in manifest["recommendations"].values():
        assert "reanalysis" not in context
        assert "taste_reanalysis_due" not in context["limitations"]


def test_manifest_never_exports_internal_viewer_digests(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root)
    manifest=_web_export_module().build_web_manifest(root/"media")
    assert "viewer_digests" not in _all_keys(manifest)
