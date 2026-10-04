from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import pytest

from media.repository.yaml_repo import YamlRepository
from media.service.recommendation_pool import filter_eligible_candidate_rows
from media.tools.build_index import build_index_rows
from media.tools.common import dump_yaml, load_yaml
from tests.media.fixture_repo import copy_fixture_repo, prepare_derived


def _audit_module():
    return import_module("media.tools.audit_intelligence")


def _add_collection(root: Path) -> None:
    path = root / "media/data/collections/sample.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    dump_yaml(
        path,
        {
            "schema_version": 4,
            "id": "sample-collection",
            "entity_type": "collection",
            "name_ru": "Тестовая коллекция",
            "name_original": "Sample Collection",
            "member_ids": ["arrival-2016"],
        },
    )


def _add_primary_rating_and_feedback(root: Path) -> None:
    path = root / "media/data/works/unwatched-fit-2020.yaml"
    work = load_yaml(path)
    work["viewer_signals"] = {
        "primary": {
            "viewing": {"status": "watched"},
            "rating": {"score": 8.0, "source": "explicit", "confidence": "exact"},
            "feedback": {
                "summary": "Интрига работает",
                "signals": [
                    {
                        "term": "story.intrigue",
                        "sentiment": "positive",
                        "strength": 2,
                        "source": "explicit",
                        "confidence": "high",
                    }
                ],
            },
        }
    }
    dump_yaml(path, work)


def _add_similarity_and_interaction(root: Path) -> None:
    similarity = root / "media/data/relations/similarity/primary.yaml"
    similarity.parent.mkdir(parents=True, exist_ok=True)
    dump_yaml(
        similarity,
        {
            "schema_version": 1,
            "target": "primary",
            "relations": [
                {
                    "type": "similar",
                    "left": {"kind": "canonical", "work_id": "arrival-2016"},
                    "right": {"kind": "canonical", "work_id": "unwatched-fit-2020"},
                    "terms": ["story.intrigue"],
                    "note": None,
                    "updated_at": "2026-10-04T10:00:00+00:00",
                    "provenance": {"source": "explicit"},
                }
            ],
        },
    )
    interactions = root / "media/data/interactions/2026-10.jsonl"
    interactions.parent.mkdir(parents=True, exist_ok=True)
    interactions.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "id": "evt-audit-1",
                "entity_type": "interaction",
                "at": "2026-10-04T10:30:00+00:00",
                "target": "primary",
                "type": "selected",
                "work_id": "unwatched-fit-2020",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def test_audit_separates_works_collections_and_entities(tmp_path):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    _add_collection(root)

    result = audit.collect_intelligence_audit(root)

    inventory = result["inventory"]
    assert inventory["works_total"] == len(list((root / "media/data/works").glob("*.yaml")))
    assert inventory["collections_total"] == 1
    assert inventory["entities_total"] == inventory["works_total"] + inventory["collections_total"]


def test_audit_reports_explicit_coverage_numerators_and_denominators(tmp_path):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    _add_collection(root)
    _add_primary_rating_and_feedback(root)

    result = audit.collect_intelligence_audit(root)
    works_total = result["inventory"]["works_total"]

    assert result["semantic_coverage"]["works"]["denominator"] == works_total
    assert result["ratings"]["primary"]["works"]["denominator"] == works_total
    assert result["ratings"]["primary"]["works"]["numerator"] >= 1
    assert result["ratings"]["primary"]["by_source"]["explicit"] >= 1
    assert result["feedback"]["primary"]["works"]["denominator"] == works_total
    assert result["feedback"]["primary"]["works"]["numerator"] >= 1
    assert result["viewing"]["primary"]["works"]["denominator"] == works_total
    assert result["viewing"]["primary"]["works"]["numerator"] >= 1


def test_audit_canonical_pool_is_unwatched_unlimited_and_runtime_unfiltered(tmp_path):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    media_root = root / "media"
    repo = YamlRepository(media_root)
    viewers, groups = repo.configured_targets()
    expected_rows = filter_eligible_candidate_rows(
        build_index_rows(media_root),
        target="primary",
        viewers=viewers,
        groups=groups,
        only_unwatched=True,
        include_not_interested=False,
        runtime_max=None,
    )

    result = audit.collect_intelligence_audit(root)

    assert result["recommendation_pool"]["primary"]["pool_total"] == len(expected_rows)
    assert result["recommendation_pool"]["primary"]["pool_total"] > 0


def test_audit_pool_ignores_stale_generated_index_and_uses_canonical_rows(tmp_path):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    index = root / "media/generated/index.jsonl"
    index.write_text("", encoding="utf-8")

    result = audit.collect_intelligence_audit(root)

    assert result["recommendation_pool"]["primary"]["pool_total"] > 0
    assert index not in audit.audit_input_paths(root)


def test_audit_counts_similarity_interactions_and_profile_confidence(tmp_path):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    _add_primary_rating_and_feedback(root)
    _add_similarity_and_interaction(root)

    result = audit.collect_intelligence_audit(root)

    assert result["similarity"]["relations_total"] == 1
    assert result["similarity"]["by_target"]["primary"] == 1
    assert result["interactions"]["events_total"] == 1
    assert result["interactions"]["by_type"]["selected"] == 1
    assert result["profiles"]["primary"]["affinities_total"] >= 1
    assert sum(result["profiles"]["primary"]["confidence"].values()) == result["profiles"]["primary"]["affinities_total"]


def test_digest_changes_when_declared_canonical_inputs_change(tmp_path):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    baseline = audit.canonical_input_digest(root)

    viewers = root / "media/config/viewers.yaml"
    viewers.write_text(viewers.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert audit.canonical_input_digest(root) != baseline

    root = copy_fixture_repo(tmp_path / "second")
    baseline = audit.canonical_input_digest(root)
    work = root / "media/data/works/unwatched-fit-2020.yaml"
    work.write_text(work.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert audit.canonical_input_digest(root) != baseline


def test_digest_is_stable_under_inventory_order_and_unrelated_file_changes(tmp_path, monkeypatch):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    baseline = audit.canonical_input_digest(root)
    original = audit.audit_input_paths

    monkeypatch.setattr(audit, "audit_input_paths", lambda repo_root: tuple(reversed(original(repo_root))))
    assert audit.canonical_input_digest(root) == baseline

    (root / "audit-note.txt").write_text("not an audit input\n", encoding="utf-8")
    assert audit.canonical_input_digest(root) == baseline


def test_audit_repository_reads_are_digest_covered_or_explicitly_exempt(tmp_path, monkeypatch):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    root_resolved = root.resolve()
    reads: set[str] = set()
    original_open = Path.open

    def traced_open(path: Path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if "r" in mode:
            try:
                rel = path.resolve().relative_to(root_resolved).as_posix()
            except ValueError:
                pass
            else:
                reads.add(rel)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", traced_open)
    audit.collect_intelligence_audit(root)

    covered = {
        path.resolve().relative_to(root_resolved).as_posix()
        for path in audit.audit_input_paths(root)
    }
    unexpected = {
        path
        for path in reads
        if path not in covered and not path.startswith("media/schemas/")
    }
    assert unexpected == set()


def test_invalid_canonical_state_fails_closed(tmp_path):
    audit = _audit_module()
    root = copy_fixture_repo(tmp_path)
    path = root / "media/data/works/unwatched-fit-2020.yaml"
    work = load_yaml(path)
    work["unexpected_field"] = True
    dump_yaml(path, work)

    with pytest.raises(ValueError, match="invalid canonical media state"):
        audit.collect_intelligence_audit(root)
