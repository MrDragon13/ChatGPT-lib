from __future__ import annotations

from pathlib import Path

ROOT=Path(__file__).parents[2]; WORKFLOWS=ROOT/".github"/"workflows"
def _text(name:str)->str: return (WORKFLOWS/name).read_text(encoding="utf-8")
def _op_kind_case(text:str)->str:
    start=text.index('case "$OP_KIND" in')
    end=text.index('echo "eligible=true"',start)
    return text[start:end]
def test_media_check_is_read_only_and_runs_full_gate():
    text=_text("media-check.yml"); assert "contents: read" in text; assert "contents: write" not in text; assert "python -m pytest -q" in text; assert "python -m media.tools.validate ." in text; assert "python -m media.cli rebuild --check" in text; assert "python -m media.cli doctor --format json" in text; assert "expected_sha" in text; assert "actions/checkout@v7" in text; assert "actions/setup-python@v7" in text
def test_media_check_is_dispatch_only_to_avoid_non_authoritative_pull_request_runs():
    text=_text("media-check.yml")
    trigger_block=text.split("on:",1)[1].split("permissions:",1)[0]
    assert "workflow_dispatch:" in trigger_block
    assert "pull_request:" not in trigger_block
    assert "github.event_name != 'pull_request'" not in text
    assert "github.event.pull_request.head.sha" not in text
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
def test_media_command_configures_bot_identity_before_replay_merge():
    text=_text("media-command.yml")
    merge_index=text.index("git merge --no-edit origin/main")
    assert text.index('git config user.name "github-actions[bot]"') < merge_index
    assert text.index('git config user.email "41898282+github-actions[bot]@users.noreply.github.com"') < merge_index
def test_media_command_dispatches_read_only_check_for_new_head_and_has_no_auto_merge():
    text=_text("media-command.yml"); assert "media-check.yml" in text; assert "expected_sha" in text; assert "gh workflow run" in text; assert "auto-merge" not in text.lower(); assert "merge_pull_request" not in text
def test_refresh_metadata_is_explicitly_not_auto_merge_eligible():
    text=_text("media-auto-merge.yml")
    case_block=_op_kind_case(text)
    assert "refresh_metadata" not in case_block
def test_maintenance_is_manual_and_read_only():
    text=_text("media-maintenance.yml"); assert "workflow_dispatch:" in text; assert "contents: read" in text; assert "contents: write" not in text; assert "doctor" in text; assert "rebuild --check" in text

def test_web_feedback_broker_can_rely_on_one_request_operation_contract():
    text=_text("media-command.yml")
    assert "Require exactly one pending request" in text
    assert "Expected exactly one pending .media/requests/*.json file" in text
    assert "find .media/requests -maxdepth 1 -type f -name '*.json'" in text

def test_record_viewing_feedback_remains_normal_data_auto_merge_eligible():
    text=_text("media-auto-merge.yml")
    case_block=_op_kind_case(text)
    assert "record_viewing_feedback" in case_block

def test_v5_normal_data_operations_are_guarded_auto_merge_eligible():
    text=_text("media-auto-merge.yml")
    case_block=_op_kind_case(text)
    for operation in (
        "edit_viewing_feedback",
        "set_inferred_preferences",
        "set_semantic_fingerprint",
        "record_recommendation_interaction",
    ):
        assert operation in case_block
    assert "refresh_metadata" not in case_block


def test_v5_auto_merge_path_allowlist_covers_only_new_canonical_data_outputs():
    text=_text("media-auto-merge.yml")
    assert "media/preferences/inferred/*.yaml" in text
    assert "media/data/interactions/*.jsonl" in text
    assert "media/data/works/*.yaml" in text
    for forbidden in (
        "media/schemas/*.json",
        "media/commands/schemas/*.json",
        "media/vocabulary.yaml)",
        "media/service/*.py",
        "media/domain/*.py",
    ):
        assert forbidden not in text
def test_broker_check_is_read_only_and_secret_free():
    text=_text("broker-check.yml")
    assert "contents: read" in text
    assert "contents: write" not in text
    assert "npm ci" in text
    assert "npm run test:run" in text
    assert "npm run typecheck" in text
    assert "CLOUDFLARE_API_TOKEN" not in text
    assert "GITHUB_APP_PRIVATE_KEY" not in text
    assert "GITHUB_APP_CLIENT_SECRET" not in text
def test_broker_deploy_is_manual_main_sha_gated_and_uses_only_cloudflare_deploy_secrets():
    text=_text("broker-deploy.yml")
    assert "workflow_dispatch:" in text
    assert "expected_sha" in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "git rev-parse HEAD" in text
    assert "npm ci" in text
    assert "npm run test:run" in text
    assert "npm run typecheck" in text
    assert "wrangler deploy" in text
    assert "secrets.CLOUDFLARE_API_TOKEN" in text
    assert "secrets.CLOUDFLARE_ACCOUNT_ID" in text
    assert "GITHUB_APP_PRIVATE_KEY" not in text
    assert "GITHUB_APP_CLIENT_SECRET" not in text
def test_pages_deploy_remains_independent_of_cloudflare_credentials():
    text=_text("media-pages.yml")
    assert "CLOUDFLARE_API_TOKEN" not in text
    assert "CLOUDFLARE_ACCOUNT_ID" not in text
