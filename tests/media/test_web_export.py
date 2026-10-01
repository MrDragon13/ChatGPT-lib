from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any

from tests.media.fixture_repo import copy_fixture_repo, prepare_derived


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


def test_manifest_uses_configured_targets_vocabulary_and_canonical_signals(tmp_path):
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    module = _web_export_module()

    manifest = module.build_web_manifest(root / "media")

    assert manifest["schema_version"] == 1
    assert manifest["default_target"] == "couple"
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


def test_manifest_handles_work_with_missing_optional_metadata(tmp_path):
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
