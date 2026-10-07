from datetime import datetime, timezone

import pytest

from media.commands.schema import parse_command
from media.domain.errors import CommandValidationError
from media.service.transaction import execute_command
from media.tools.common import dump_yaml, load_yaml
from media.tools.rebuild import check_generated, rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo

UUID1 = "123e4567-e89b-42d3-a456-426614174010"
UUID2 = "123e4567-e89b-42d3-a456-426614174011"


def fingerprint(*traits, operation_id=UUID1):
    return parse_command({
        "schema_version": 1,
        "operation_id": operation_id,
        "operation": "set_semantic_fingerprint",
        "work_ref": {"id": "arrival-2016"},
        "traits": list(traits),
    })


def test_set_semantic_fingerprint_replaces_traits_and_preserves_viewer_signals(tmp_path):
    root = copy_fixture_repo(tmp_path)
    before = load_yaml(root / "media/data/works/arrival-2016.yaml")["viewer_signals"]
    command = fingerprint(
        {"term":"story.intrigue","source":"llm_inferred","confidence":"high"},
        {"term":"pacing.slow","source":"llm_inferred","confidence":"medium"},
    )
    result = execute_command(root, command, now=datetime(2026,10,3,tzinfo=timezone.utc))
    work = load_yaml(root / "media/data/works/arrival-2016.yaml")
    assert work["metadata"]["semantic"]["traits"] == [
        {"term":"story.intrigue","source":"llm_inferred","confidence":"high"},
        {"term":"pacing.slow","source":"llm_inferred","confidence":"medium"},
    ]
    assert work["viewer_signals"] == before
    assert result.status == "applied"


def test_set_semantic_fingerprint_rebuilds_rating_dependent_profiles(tmp_path):
    root = copy_fixture_repo(tmp_path)
    work_path = root / "media/data/works/arrival-2016.yaml"
    work = load_yaml(work_path)
    work["viewer_signals"]["primary"]["rating"] = {
        "score": 9,
        "source": "explicit",
        "confidence": "exact",
    }
    dump_yaml(work_path, work)
    rebuild_generated(root / "media")

    result = execute_command(
        root,
        fingerprint({"term":"pacing.fast","source":"llm_inferred","confidence":"high"}),
        now=datetime(2026,10,3,tzinfo=timezone.utc),
    )

    assert "media/generated/profiles/primary.yaml" in result.changed_files
    assert "media/generated/profiles/couple.yaml" in result.changed_files
    assert "media/generated/profiles/partner.yaml" not in result.changed_files
    assert check_generated(root / "media") == []


def test_set_semantic_fingerprint_rejects_unknown_vocabulary_term(tmp_path):
    root = copy_fixture_repo(tmp_path)
    with pytest.raises(CommandValidationError):
        execute_command(root, fingerprint({"term":"story.nonexistent","source":"llm_inferred","confidence":"medium"}))


def test_set_semantic_fingerprint_rejects_viewer_reaction_terms(tmp_path):
    root = copy_fixture_repo(tmp_path)
    with pytest.raises(CommandValidationError):
        execute_command(root, fingerprint({"term":"reaction.cringe","source":"llm_inferred","confidence":"medium"}))


def test_set_semantic_fingerprint_allows_empty_replacement(tmp_path):
    root = copy_fixture_repo(tmp_path)
    execute_command(root, fingerprint(), now=datetime(2026,10,3,tzinfo=timezone.utc))
    work = load_yaml(root / "media/data/works/arrival-2016.yaml")
    assert work["metadata"]["semantic"]["traits"] == []


def test_semantic_fingerprint_receipt_details_bind_work_for_changed_and_no_change(tmp_path):
    from media.service.transaction import preview_command

    root = copy_fixture_repo(tmp_path)
    traits = ({"term":"story.intrigue","source":"llm_inferred","confidence":"high"},)
    changed = preview_command(root, fingerprint(*traits, operation_id=UUID1), now=datetime(2026,10,3,tzinfo=timezone.utc))
    assert changed.details["work_id"] == "arrival-2016"

    execute_command(root, fingerprint(*traits, operation_id=UUID1), now=datetime(2026,10,3,tzinfo=timezone.utc))
    no_change = preview_command(root, fingerprint(*traits, operation_id=UUID2), now=datetime(2026,10,3,tzinfo=timezone.utc))
    assert no_change.status == "no_change"
    assert no_change.details["work_id"] == "arrival-2016"
