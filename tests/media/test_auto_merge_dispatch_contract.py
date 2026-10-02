from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_media_command_only_dispatches_read_only_check_for_exact_applied_head():
    text = _text("media-command.yml")
    assert 'gh workflow run media-check.yml --ref "$BRANCH" -f expected_sha="$HEAD_SHA"' in text
    assert "media-auto-merge.yml" not in text


def test_auto_merge_starts_after_command_and_waits_for_authoritative_check():
    text = _text("media-auto-merge.yml")
    assert "workflow_run:" in text
    assert "workflows: [Media Command]" in text
    assert "github.event.workflow_run.event == 'pull_request'" in text
    assert "media-check.yml" in text
    assert "workflow_dispatch" in text
    assert "CHECKED_SHA" in text
    assert "head_sha" in text
    assert "actions: write" in text
    assert "run-name:" in text
    assert "github.event.workflow_run.head_branch" in text


def test_auto_merge_dispatches_pages_for_exact_merge_sha():
    auto_merge = _text("media-auto-merge.yml")
    pages = _text("media-pages.yml")

    assert "MERGE_SHA" in auto_merge
    assert 'gh workflow run media-pages.yml --ref main -f expected_sha="$MERGE_SHA"' in auto_merge
    assert "expected_sha:" in pages
    assert "inputs.expected_sha" in pages
    assert "run-name:" in pages
    assert "github.sha" in pages
