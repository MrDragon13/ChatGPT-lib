from pathlib import Path

import json
import pytest

from media.domain.errors import PathPolicyError
import media.service.path_policy as path_policy
from media.service.path_policy import allowed_paths_for_operation, verify_changed_paths, verify_operation_specific_paths


EXPECTED_POLICY = {
    "record_media_entry": {
        "auto_merge": True,
        "execution_class": "v6_single_runner",
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
            "media/data/relations/similarity/*.yaml",
        ],
    },
    "add_work": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
            "media/data/relations/similarity/*.yaml",
        ],
    },
    "record_viewing_feedback": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
            "media/data/relations/similarity/*.yaml",
        ],
    },
    "edit_viewing_feedback": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "set_interest": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "refresh_metadata": {
        "auto_merge": False,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "refresh_work_metadata": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            ".media/operations/*.json",
        ],
    },
    "set_semantic_fingerprint": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "set_inferred_preferences": {
        "auto_merge": True,
        "execution_class": "v6_single_runner",
        "allowed_paths": [
            "media/preferences/inferred/*.yaml",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "record_recommendation_interaction": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/interactions/*.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "set_work_similarity": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/relations/similarity/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "remove_work_similarity": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/relations/similarity/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "reserve_reassessment_session": {
        "auto_merge": True,
        "allowed_paths": [
            "media/pilots/legacy-reassessment-primary.json",
            ".media/operations/*.json",
        ],
    },
    "complete_reassessment_item": {
        "auto_merge": True,
        "allowed_paths": [
            "media/pilots/legacy-reassessment-primary.json",
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "record_reassessment_modernization": {
        "auto_merge": True,
        "allowed_paths": [
            "media/pilots/legacy-reassessment-primary.json",
            ".media/operations/*.json",
        ],
    },
    "close_reassessment_session": {
        "auto_merge": True,
        "allowed_paths": [
            "media/pilots/legacy-reassessment-primary.json",
            ".media/operations/*.json",
        ],
    },
}

CASES_PATH = Path(__file__).parent / "fixtures" / "operation_path_policy_cases.json"


def _policy_path() -> Path:
    return Path(path_policy.__file__).resolve().parents[1] / "config" / "operation_path_policy.json"


def _cases() -> list[dict]:
    document=json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert document["schema_version"]==1
    return document["cases"]


def test_declarative_policy_document_is_the_complete_operation_contract():
    policy=json.loads(_policy_path().read_text(encoding="utf-8"))
    assert policy=={"schema_version":1,"operations":EXPECTED_POLICY}
    for operation, entry in EXPECTED_POLICY.items():
        assert allowed_paths_for_operation(operation)==tuple(entry["allowed_paths"])


def test_shared_parity_corpus_matches_python_policy_matcher():
    for case in _cases():
        assert path_policy.matches_policy_path(case["path"],case["pattern"]) is case["expected"], case


def test_parity_corpus_covers_every_auto_merge_operation_pattern_and_protected_classes():
    positive={(case["operation"],case["pattern"]) for case in _cases() if case["expected"]}
    for operation,entry in EXPECTED_POLICY.items():
        if not entry["auto_merge"]:
            continue
        for pattern in entry["allowed_paths"]:
            assert (operation,pattern) in positive

    negatives={case["path"] for case in _cases() if not case["expected"]}
    for path in (
        "evil/media/data/works/x.yaml",
        "media/data/works/sub/x.yaml",
        "media/data/works/x.yaml.bak",
        "media/config/operation_path_policy.json",
        ".github/workflows/media-auto-merge.yml",
        "media/service/path_policy.py",
        "media/tools/rebuild.py",
        "tests/media/test_path_policy.py",
    ):
        assert path in negatives


@pytest.mark.parametrize("pattern",[
    "media/data/works/**.yaml",
    "media/data/works/*/*.yaml",
    "media/data/works/?.yaml",
    "media/data/works/[ab].yaml",
    "media/data/works/{a,b}.yaml",
])
def test_unsupported_pattern_grammar_fails_closed_in_python_matcher(pattern):
    with pytest.raises(PathPolicyError):
        path_policy.matches_policy_path("media/data/works/a.yaml",pattern)


@pytest.mark.parametrize("path",[
    "/media/data/works/a.yaml",
    "../media/data/works/a.yaml",
    "media/data/works/../a.yaml",
    "media//data/works/a.yaml",
])
def test_non_repository_relative_or_non_normalized_paths_fail_closed(path):
    with pytest.raises(PathPolicyError):
        path_policy.matches_policy_path(path,"media/data/works/*.yaml")


def test_policy_loader_rejects_unsupported_pattern_grammar(tmp_path,monkeypatch):
    document={"schema_version":1,"operations":{"set_interest":{"auto_merge":True,"allowed_paths":["media/data/works/**.yaml"]}}}
    policy=tmp_path/"policy.json"
    policy.write_text(json.dumps(document),encoding="utf-8")
    monkeypatch.setattr(path_policy,"_POLICY_PATH",policy,raising=False)
    with pytest.raises(PathPolicyError):
        allowed_paths_for_operation("set_interest")


def test_set_inferred_preferences_runtime_scope_excludes_generated_index():
    allowed_paths_for_operation("set_inferred_preferences")
    verify_changed_paths("set_inferred_preferences",[
        "media/preferences/inferred/primary.yaml",
        "media/generated/profiles/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174001.json",
    ])
    with pytest.raises(PathPolicyError):
        verify_changed_paths("set_inferred_preferences",["media/generated/index.jsonl"])


def test_missing_policy_file_fails_closed(tmp_path,monkeypatch):
    monkeypatch.setattr(path_policy,"_POLICY_PATH",tmp_path/"missing.json",raising=False)
    with pytest.raises(PathPolicyError):
        allowed_paths_for_operation("set_interest")


@pytest.mark.parametrize("document",[
    {},
    {"schema_version":2,"operations":EXPECTED_POLICY},
    {"schema_version":1,"operations":[]},
    {"schema_version":1,"operations":{"set_interest":{"auto_merge":True,"allowed_paths":[]}}},
])
def test_malformed_policy_fails_closed(tmp_path,monkeypatch,document):
    policy=tmp_path/"policy.json"
    policy.write_text(json.dumps(document),encoding="utf-8")
    monkeypatch.setattr(path_policy,"_POLICY_PATH",policy,raising=False)
    with pytest.raises(PathPolicyError):
        allowed_paths_for_operation("set_interest")


def test_unknown_operation_fails_closed():
    assert allowed_paths_for_operation("ghost") == ()
    with pytest.raises(PathPolicyError):
        verify_changed_paths("ghost",["media/data/works/arrival-2016.yaml"])


def test_normal_operations_reject_policy_workflow_service_tooling_and_guard_paths():
    protected=(
        "media/config/operation_path_policy.json",
        ".github/workflows/media-auto-merge.yml",
        "media/service/path_policy.py",
        "media/tools/rebuild.py",
        "tests/media/test_path_policy.py",
        "tests/media/test_auto_merge_dispatch_contract.py",
    )
    for operation,entry in EXPECTED_POLICY.items():
        if not entry["auto_merge"]:
            continue
        for path in protected:
            with pytest.raises(PathPolicyError):
                verify_changed_paths(operation,[path])


def test_edit_feedback_allows_only_work_generated_and_receipt_paths():
    verify_changed_paths("edit_viewing_feedback", [
        "media/data/works/arrival-2016.yaml",
        "media/generated/index.jsonl",
        "media/generated/profiles/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174001.json",
    ])
    with pytest.raises(PathPolicyError):
        verify_changed_paths("edit_viewing_feedback", ["media/preferences/inferred/primary.yaml"])


def test_existing_feedback_operation_cannot_modify_future_intelligence_paths():
    for path in (
        "media/preferences/inferred/primary.yaml",
        "media/data/interactions/2026-10.jsonl",
        "media/pilots/legacy-reassessment-primary.json",
    ):
        with pytest.raises(PathPolicyError):
            verify_changed_paths("record_viewing_feedback", [path])


def test_similarity_operations_allow_only_relation_and_receipt_paths():
    allowed = [
        "media/data/relations/similarity/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174040.json",
    ]
    verify_changed_paths("set_work_similarity", allowed)
    verify_changed_paths("remove_work_similarity", allowed)

    for operation in ("set_work_similarity", "remove_work_similarity"):
        for forbidden in (
            "media/data/works/arrival-2016.yaml",
            "media/generated/index.jsonl",
            "media/preferences/inferred/primary.yaml",
            "media/pilots/legacy-reassessment-primary.json",
        ):
            with pytest.raises(PathPolicyError):
                verify_changed_paths(operation, [forbidden])


def test_work_creation_paths_allow_similarity_reconciliation_but_regular_edits_do_not():
    relation_path = "media/data/relations/similarity/primary.yaml"
    verify_changed_paths("add_work", [relation_path])
    verify_changed_paths("record_viewing_feedback", [relation_path])

    for operation in ("edit_viewing_feedback", "set_interest", "set_semantic_fingerprint"):
        with pytest.raises(PathPolicyError):
            verify_changed_paths(operation, [relation_path])


def test_refresh_work_metadata_shape_guard_allows_only_receipt_or_selected_work_outputs():
    receipt = ".media/operations/123e4567-e89b-42d3-a456-426614174099.json"
    verify_changed_paths("refresh_work_metadata", [receipt])
    verify_operation_specific_paths("refresh_work_metadata", [receipt], {"work_id": "arrival-2016"})
    allowed = ["media/data/works/arrival-2016.yaml", "media/generated/index.jsonl", receipt]
    verify_changed_paths("refresh_work_metadata", allowed)
    verify_operation_specific_paths("refresh_work_metadata", allowed, {"work_id": "arrival-2016"})
    with pytest.raises(PathPolicyError, match="selected work"):
        verify_operation_specific_paths(
            "refresh_work_metadata",
            ["media/data/works/batman-2022.yaml", receipt],
            {"work_id": "arrival-2016"},
        )
    with pytest.raises(PathPolicyError, match="at most one"):
        verify_operation_specific_paths(
            "refresh_work_metadata",
            ["media/data/works/arrival-2016.yaml", "media/data/works/batman-2022.yaml", receipt],
            {"work_id": "arrival-2016"},
        )


def test_record_media_entry_policy_allows_atomic_work_and_generated_outputs():
    allowed = [
        "media/data/works/arrival-2016.yaml",
        "media/generated/index.jsonl",
        "media/generated/profiles/primary.yaml",
        "media/data/relations/similarity/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174301.json",
    ]
    verify_changed_paths("record_media_entry", allowed)
    with pytest.raises(PathPolicyError):
        verify_changed_paths("record_media_entry", ["media/preferences/inferred/primary.yaml"])
