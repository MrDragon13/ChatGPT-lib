from __future__ import annotations

from tests.media.fixture_repo import copy_fixture_repo, prepare_derived


def test_web_manifest_defaults_to_primary_viewer(tmp_path):
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)

    from media.service.web_export import build_web_manifest

    manifest = build_web_manifest(root / "media")

    assert manifest["default_target"] == "primary"
