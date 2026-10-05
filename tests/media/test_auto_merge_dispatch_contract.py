from __future__ import annotations

import json
from pathlib import Path
import subprocess
import textwrap

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
POLICY_CASES = ROOT / "tests" / "media" / "fixtures" / "operation_path_policy_cases.json"


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _cases() -> list[dict]:
    document=json.loads(POLICY_CASES.read_text(encoding="utf-8"))
    assert document["schema_version"]==1
    return document["cases"]


def _workflow_match_function() -> str:
    text=_text("media-auto-merge.yml")
    start_marker="          match_policy_path() {"
    start=text.index(start_marker)
    end=text.index("\n          }\n",start)+len("\n          }")
    return textwrap.dedent(text[start:end])


def _workflow_match(path: str, pattern: str) -> int:
    script=f"set -u\n{_workflow_match_function()}\nmatch_policy_path \"$1\" \"$2\""
    result=subprocess.run(
        ["bash","-c",script,"policy-matcher",path,pattern],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode


def _reservation_receipt_jq_filter() -> str:
    text = _text("media-auto-merge.yml")
    reserve_start = text.index('            if [ "$OP_KIND" = "reserve_reassessment_session" ]; then')
    filter_marker = "              if ! printf '%s' \"$OP_JSON\" | jq -e '\n"
    filter_start = text.index(filter_marker, reserve_start) + len(filter_marker)
    filter_end = text.index("\n              ' >/dev/null; then", filter_start)
    return textwrap.dedent(text[filter_start:filter_end])


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


def test_auto_merge_trust_boundary_uses_main_policy_and_pr_file_metadata():
    text = _text("media-auto-merge.yml")
    assert 'media/config/operation_path_policy.json?ref=main' in text
    assert 'gh api --paginate "repos/$REPO/pulls/$PR_NUMBER/files?per_page=100" --jq \' .[].filename\'' not in text
    assert 'gh api --paginate "repos/$REPO/pulls/$PR_NUMBER/files?per_page=100" --jq \'.[].filename\'' in text
    assert '?ref=$PR_HEAD_SHA' in text
    assert "base64 --decode" in text
    assert "jq -e" in text
    assert "auto_merge" in text
    assert "allowed_paths" in text
    assert 'case "$OP_KIND" in' not in text
    for old_arm in (
        "add_work|record_viewing_feedback)",
        "edit_viewing_feedback|set_interest|set_semantic_fingerprint)",
        "set_work_similarity|remove_work_similarity)",
        "set_inferred_preferences)",
        "record_recommendation_interaction)",
    ):
        assert old_arm not in text


def test_privileged_workflow_matcher_matches_shared_policy_corpus():
    for case in _cases():
        assert (_workflow_match(case["path"],case["pattern"])==0) is case["expected"], case


def test_privileged_workflow_matcher_rejects_unsupported_pattern_grammar():
    for pattern in (
        "media/data/works/**.yaml",
        "media/data/works/*/*.yaml",
        "media/data/works/?.yaml",
        "media/data/works/[ab].yaml",
        "media/data/works/{a,b}.yaml",
    ):
        assert _workflow_match("media/data/works/a.yaml",pattern) != 0


def test_reassessment_reservation_receipt_validator_accepts_valid_reserved_item_digests():
    payload = {
        "details": {
            "reserved_items": {
                "gattaca-1997": {
                    "pre_review_work_file_digest": "sha256:" + ("a" * 64),
                }
            }
        }
    }
    result = subprocess.run(
        ["jq", "-e", _reservation_receipt_jq_filter()],
        cwd=ROOT,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_auto_merge_dispatches_pages_for_exact_merge_sha_in_media_mode():
    auto_merge = _text("media-auto-merge.yml")
    pages = _text("media-pages.yml")

    assert "MERGE_SHA" in auto_merge
    assert 'REPO: ${{ github.repository }}\n          MERGE_SHA:' in auto_merge
    assert 'gh workflow run media-pages.yml --repo "$REPO" --ref main -f expected_sha="$MERGE_SHA" -f publish_mode=media' in auto_merge
    assert "expected_sha:" in pages
    assert "publish_mode:" in pages
    assert "inputs.expected_sha" in pages
    assert "inputs.publish_mode != 'media'" in pages
    assert "run-name:" in pages
    assert "github.sha" in pages


def test_media_publish_mode_skips_only_redundant_heavy_checks():
    pages = _text("media-pages.yml")

    for step_name in (
        "Run project tests",
        "Run web tests",
        "Typecheck web",
        "Install Chromium for browser checks",
        "Run browser checks",
    ):
        marker = f"- name: {step_name}"
        start = pages.index(marker)
        block = pages[start: start + 260]
        assert "if: ${{ inputs.publish_mode != 'media' }}" in block

    for required_step in (
        "Validate canonical media",
        "Check generated artifacts",
        "Run media doctor",
        "Export web manifest",
        "Build publishable web artifact",
        "Scan static artifact",
        "Upload GitHub Pages artifact",
    ):
        assert f"- name: {required_step}" in pages
