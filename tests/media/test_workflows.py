from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).parents[2]; WORKFLOWS=ROOT/".github"/"workflows"
def _text(name:str)->str: return (WORKFLOWS/name).read_text(encoding="utf-8")
def _policy()->dict: return json.loads((ROOT/"media/config/operation_path_policy.json").read_text(encoding="utf-8"))
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
def test_media_command_stages_all_v5_canonical_outputs():
    text=_text("media-command.yml")
    assert "media/preferences/inferred" in text
    assert "media/data/interactions" in text
def test_media_command_handles_optional_v5_output_directories_without_pathspec_failure():
    text=_text("media-command.yml")
    stage=text.split("- name: Stage operation outputs",1)[1].split("- name: Verify staged path policy",1)[0]
    assert "STAGE_PATHS=(" in stage
    assert "for path in media/data/interactions media/preferences/inferred" in stage
    assert 'git ls-files -- "$path" | grep -q .' in stage
    assert 'git add -A -- "${STAGE_PATHS[@]}"' in stage
def test_media_command_stages_similarity_outputs_as_optional_canonical_data():
    text=_text("media-command.yml")
    stage=text.split("- name: Stage operation outputs",1)[1].split("- name: Verify staged path policy",1)[0]
    assert "media/data/relations/similarity" in stage
    assert 'git ls-files -- "$path" | grep -q .' in stage
def test_media_command_configures_bot_identity_before_replay_merge():
    text=_text("media-command.yml")
    merge_index=text.index("git merge --no-edit origin/main")
    assert text.index('git config user.name "github-actions[bot]"') < merge_index
    assert text.index('git config user.email "41898282+github-actions[bot]@users.noreply.github.com"') < merge_index
def test_media_command_dispatches_read_only_check_for_new_head_and_has_no_auto_merge():
    text=_text("media-command.yml"); assert "media-check.yml" in text; assert "expected_sha" in text; assert "gh workflow run" in text; assert "auto-merge" not in text.lower(); assert "merge_pull_request" not in text

def test_refresh_metadata_is_explicitly_not_auto_merge_eligible():
    assert _policy()["operations"]["refresh_metadata"]["auto_merge"] is False

def test_maintenance_is_manual_and_read_only():
    text=_text("media-maintenance.yml"); assert "workflow_dispatch:" in text; assert "contents: read" in text; assert "contents: write" not in text; assert "doctor" in text; assert "rebuild --check" in text

def test_web_feedback_broker_can_rely_on_one_request_operation_contract():
    text=_text("media-command.yml")
    assert "Require exactly one pending request" in text
    assert "Expected exactly one pending .media/requests/*.json file" in text
    assert "find .media/requests -maxdepth 1 -type f -name '*.json'" in text

def test_record_viewing_feedback_remains_normal_data_auto_merge_eligible():
    assert _policy()["operations"]["record_viewing_feedback"]["auto_merge"] is True

def test_v5_normal_data_operations_are_guarded_auto_merge_eligible():
    operations=_policy()["operations"]
    for operation in (
        "edit_viewing_feedback",
        "set_inferred_preferences",
        "set_semantic_fingerprint",
        "record_recommendation_interaction",
    ):
        assert operations[operation]["auto_merge"] is True
    assert operations["refresh_metadata"]["auto_merge"] is False


def test_similarity_operations_are_guarded_auto_merge_eligible_on_relation_paths_only():
    operations=_policy()["operations"]
    for operation in ("set_work_similarity","remove_work_similarity"):
        entry=operations[operation]
        assert entry["auto_merge"] is True
        assert entry["allowed_paths"]==[
            "media/data/relations/similarity/*.yaml",
            ".media/operations/*.json",
        ]


def test_work_creation_policy_allows_similarity_reconciliation_without_broadening_edits():
    operations=_policy()["operations"]
    relation="media/data/relations/similarity/*.yaml"
    assert relation in operations["add_work"]["allowed_paths"]
    assert relation in operations["record_viewing_feedback"]["allowed_paths"]
    for operation in ("edit_viewing_feedback","set_interest","set_semantic_fingerprint"):
        assert relation not in operations[operation]["allowed_paths"]


def test_auto_merge_consumes_trusted_main_policy_instead_of_embedded_operation_cases():
    text=_text("media-auto-merge.yml")
    assert "media/config/operation_path_policy.json?ref=main" in text
    assert 'pulls/$PR_NUMBER/files?per_page=100' in text
    assert "auto_merge" in text
    assert "allowed_paths" in text
    assert 'case "$OP_KIND" in' not in text
    for legacy in (
        "add_work|record_viewing_feedback)",
        "edit_viewing_feedback|set_interest|set_semantic_fingerprint)",
        "set_work_similarity|remove_work_similarity)",
    ):
        assert legacy not in text


def test_media_dev_check_triggers_when_trusted_path_policy_changes():
    text=_text("media-dev-check.yml")
    trigger_block=text.split("on:",1)[1].split("permissions:",1)[0]
    assert "media/config/operation_path_policy.json" in trigger_block


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


def test_record_media_entry_provider_secret_is_gated_by_creation():
    text=_text("media-command.yml")
    assert "'record_media_entry'" in text
    assert "create_if_missing" in text
    assert "needs_provider" in text
    assert "steps.operation.outputs.needs_provider == 'true'" in text


def test_v6_media_data_pipeline_is_serialized_without_cancelling_pending_runs():
    text=_text("media-command.yml")
    concurrency=text.split("concurrency:",1)[1].split("jobs:",1)[0]
    assert "group: media-data-pipeline" in concurrency
    assert "cancel-in-progress: false" in concurrency
    assert "queue: max" in concurrency


def test_record_media_entry_uses_single_runner_execution_class():
    policy=_policy()["operations"]["record_media_entry"]
    assert policy["execution_class"]=="v6_single_runner"


def test_checkpointed_inferred_preferences_use_single_runner_execution_class():
    policy=_policy()["operations"]["set_inferred_preferences"]
    assert policy["execution_class"]=="v6_single_runner"


def test_v6_fast_path_merges_exact_checked_head_without_direct_main_push():
    text=_text("media-command.yml")
    assert "Merge checked v6 operation" in text
    assert 'pulls/$PR_NUMBER/merge' in text
    assert '"sha": "$HEAD_SHA"' in text or "'sha': head_sha" in text
    assert "merged" in text
    assert "git push origin HEAD:main" not in text
    assert "gh pr merge --auto" not in text


def test_v6_fast_path_replays_when_main_moves_before_merge():
    text=_text("media-command.yml")
    assert "Replay v6 operation on latest main" in text
    assert "MAX_ATTEMPTS" in text
    assert "git fetch origin main" in text
    assert "origin/main" in text
    assert "base_sha" in text
    assert "current_main" in text
    assert "retry" in text.lower()


def test_v6_fast_path_dispatches_pages_for_exact_merge_sha_not_media_check():
    text=_text("media-command.yml")
    fast=text.split("- name: Replay v6 operation on latest main",1)[1]
    assert "media-pages.yml" in fast
    assert "expected_sha" in fast
    assert "publish_mode=media" in fast
    legacy=text.split("- name: Dispatch read-only check for exact new head",1)[1]
    assert "media-check.yml" in legacy
    assert "steps.operation.outputs.execution_class != 'v6_single_runner'" in legacy


def test_v6_fast_path_uses_targeted_authoritative_gate_not_full_pytest_or_doctor():
    text=_text("media-command.yml")
    fast=text.split("- name: Replay v6 operation on latest main",1)[1].split("- name: Replay branch on current main",1)[0]
    assert "python -m media.tools.validate ." in fast
    assert "python -m media.cli rebuild --check" in fast
    assert "tests/media/test_record_media_entry.py" in fast
    assert "tests/media/test_inferred_preferences.py" in fast
    assert "tests/media/test_v6_reanalysis_status.py" in fast
    assert "python -m pytest -q" not in fast
    assert "media.cli doctor" not in fast
