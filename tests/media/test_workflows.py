from __future__ import annotations

from pathlib import Path

ROOT=Path(__file__).parents[2]; WORKFLOWS=ROOT/".github"/"workflows"
def _text(name:str)->str: return (WORKFLOWS/name).read_text(encoding="utf-8")
def test_media_check_is_read_only_and_runs_full_gate():
    text=_text("media-check.yml"); assert "contents: read" in text; assert "contents: write" not in text; assert "python -m pytest -q" in text; assert "python -m media.tools.validate ." in text; assert "python -m media.cli rebuild --check" in text; assert "python -m media.cli doctor --format json" in text; assert "expected_sha" in text; assert "actions/checkout@v7" in text; assert "actions/setup-python@v7" in text
def test_media_check_skips_request_only_operation_prs_but_allows_dispatched_head_checks():
    text=_text("media-check.yml"); assert "github.event_name != 'pull_request'" in text; assert "!startsWith(github.head_ref, 'media/op-')" in text
def test_media_command_has_same_repo_branch_guard_before_secrets():
    text=_text("media-command.yml"); assert "github.event.pull_request.head.repo.full_name == github.repository" in text; assert "startsWith(github.head_ref, 'media/op-')" in text; assert "TMDB_READ_TOKEN" in text; assert "env:\n          TMDB_READ_TOKEN:" in text; assert "OPENAI" not in text.upper(); assert "pull-requests: write" in text; assert "actions: write" in text
def test_media_command_gates_tmdb_secret_on_provider_need_not_operation_name_only():
    text=_text("media-command.yml"); assert "create_if_missing" in text; assert "needs_provider" in text; assert "steps.operation.outputs.needs_provider" in text
def test_refresh_metadata_is_provider_dependent_in_command_workflow():
    text=_text("media-command.yml")
    assert "operation == 'refresh_metadata'" in text
    assert "TMDB_READ_TOKEN" in text
    assert "steps.operation.outputs.needs_provider == 'true'" in text
def test_media_command_replays_on_current_main_and_controls_paths():
    text=_text("media-command.yml"); assert "git fetch origin main" in text; assert "git merge --no-edit origin/main" in text; assert "exactly one pending" in text.lower(); assert 'rm -- "$REQUEST"' in text; assert "verify_changed_paths" in text; assert "git diff --cached --name-only" in text; assert "media/schemas" in text; assert "media/vocabulary.yaml" in text; assert "media/service" in text; assert "media/domain" in text
def test_media_command_dispatches_read_only_check_for_new_head_and_has_no_auto_merge():
    text=_text("media-command.yml"); assert "media-check.yml" in text; assert "expected_sha" in text; assert "gh workflow run" in text; assert "auto-merge" not in text.lower(); assert "merge_pull_request" not in text
def test_refresh_metadata_is_explicitly_not_auto_merge_eligible():
    text=_text("media-auto-merge.yml")
    assert "add_work|record_viewing_feedback|set_interest" in text
    case_block=text.split('case "$OP_KIND" in',1)[1].split('esac',1)[0]
    assert "refresh_metadata" not in case_block
def test_maintenance_is_manual_and_read_only():
    text=_text("media-maintenance.yml"); assert "workflow_dispatch:" in text; assert "contents: read" in text; assert "contents: write" not in text; assert "doctor" in text; assert "rebuild --check" in text
