from pathlib import Path

import json


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_legacy_reassessment_runtime_is_removed():
    removed=[
        "media/service/reassessment.py",
        "media/service/reassessment_mutate.py",
        "media/service/reassessment_validation.py",
        "media/tools/reassessment.py",
        "media/tools/validate_reassessment_transition.py",
        "media/schemas/reassessment-pilot.schema.json",
        "media/commands/schemas/reserve_reassessment_session.schema.json",
        "media/commands/schemas/complete_reassessment_item.schema.json",
        "media/commands/schemas/close_reassessment_session.schema.json",
        "media/commands/schemas/record_reassessment_modernization.schema.json",
        ".github/workflows/media-check.yml",
        ".github/workflows/media-auto-merge.yml",
    ]
    assert all(not Path(path).exists() for path in removed)

    commands=_text("media/domain/commands.py")
    parser=_text("media/commands/schema.py")
    transaction=_text("media/service/transaction.py")
    cli=_text("media/cli.py")
    for token in (
        "ReserveReassessmentSessionCommand",
        "CompleteReassessmentItemCommand",
        "CloseReassessmentSessionCommand",
        "RecordReassessmentModernizationCommand",
        "reassessment-context",
        "reassessment-history",
        "reassessment-modernization-context",
    ):
        assert token not in commands+parser+transaction+cli


def test_all_auto_merge_operations_use_single_runner_after_cutover():
    policy=json.loads(_text("media/config/operation_path_policy.json"))
    assert not any("reassessment" in name for name in policy["operations"])
    for name,entry in policy["operations"].items():
        if entry["auto_merge"]:
            assert entry.get("execution_class")=="v6_single_runner", name


def test_media_command_has_no_dependency_on_removed_legacy_workflows():
    text=_text(".github/workflows/media-command.yml")
    assert "media-check.yml" not in text
    assert "media-auto-merge.yml" not in text
    assert "Merge checked v6 operation" in text
    assert "Leave manual operation ready for review" in text


def test_live_broker_feedback_route_uses_v6_mapping():
    text=_text("broker/src/index.ts")
    assert "submitFeedbackV6" in text
    assert "const result = await submitFeedbackV6(input, env);" in text
    assert "const result = await submitFeedback(input, env);" not in text


def test_cutover_archive_and_global_rules_remain_after_library_repopulation():
    assert Path("docs/archive/media-library-before-v6-reset-2026-10-07.md").exists()
    assert Path("media/preferences/explicit/primary.yaml").exists()
    assert Path("media/vocabulary.yaml").exists()

    # These were one-time v5 runtime artifacts and must not return.
    assert not Path("media/pilots/legacy-reassessment-primary.json").exists()
    assert not Path("media/baselines/intelligence-stage-a.json").exists()
    assert not Path("media/baselines/intelligence-stage-a.meta.json").exists()

    # Active v6 works/interactions/preferences/receipts are allowed to grow again.
    # Their consistency is covered by canonical validation and rebuild checks.
