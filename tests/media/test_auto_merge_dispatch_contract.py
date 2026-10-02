from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_media_command_dispatches_check_and_auto_merge_for_exact_applied_head():
    text = _text("media-command.yml")
    assert 'gh workflow run media-check.yml --ref "$BRANCH" -f expected_sha="$HEAD_SHA"' in text
    assert 'gh workflow run media-auto-merge.yml --ref "$BRANCH" -f expected_sha="$HEAD_SHA"' in text


def test_auto_merge_is_explicit_dispatch_and_waits_for_authoritative_check():
    text = _text("media-auto-merge.yml")
    assert "workflow_dispatch:" in text
    assert "expected_sha" in text
    assert "workflow_run:" not in text
    assert "media-check.yml" in text
    assert "workflow_dispatch" in text
    assert "CHECKED_SHA" in text
    assert "head_sha" in text
    assert "actions: read" in text
