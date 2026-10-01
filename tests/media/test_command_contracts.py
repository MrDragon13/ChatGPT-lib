from __future__ import annotations

import pytest

from media.commands.schema import parse_command
from media.domain.errors import CommandValidationError
from media.domain.commands import AddWorkCommand, RecommendContextRequest, RecordViewingFeedbackCommand, SetInterestCommand

VALID_UUID = "123e4567-e89b-42d3-a456-426614174000"


def valid_record_feedback_dict() -> dict:
    return {"schema_version": 1, "operation_id": VALID_UUID, "operation": "record_viewing_feedback", "work_ref": {"title": "Arrival", "year": 2016}, "target_updates": [{"target": "primary", "viewing": {"status": "watched"}, "rating": {"score": 8.5, "source": "explicit_approx", "confidence": "high"}}]}


def valid_set_interest_dict(priority: int | None = 3) -> dict:
    return {"schema_version": 1, "operation_id": VALID_UUID, "operation": "set_interest", "work_ref": {"id": "arrival-2016"}, "target": "primary", "state": "shortlist", "priority": priority}


def test_record_feedback_requires_operation_id_and_known_fields():
    data = valid_record_feedback_dict(); data.pop("operation_id")
    with pytest.raises(CommandValidationError): parse_command(data)
    data = valid_record_feedback_dict(); data["unexpected"] = True
    with pytest.raises(CommandValidationError): parse_command(data)


def test_rating_is_constrained_to_half_steps_and_existing_sources():
    bad = valid_record_feedback_dict(); bad["target_updates"][0]["rating"] = {"score": 8.3, "source": "explicit", "confidence": "exact"}
    with pytest.raises(CommandValidationError): parse_command(bad)
    bad = valid_record_feedback_dict(); bad["target_updates"][0]["rating"] = {"score": 8.5, "source": "guessed", "confidence": "high"}
    with pytest.raises(CommandValidationError): parse_command(bad)


def test_set_interest_priority_is_one_to_five():
    with pytest.raises(CommandValidationError): parse_command(valid_set_interest_dict(priority=6))


def test_unknown_operation_is_rejected():
    bad = valid_record_feedback_dict(); bad["operation"] = "delete_everything"
    with pytest.raises(CommandValidationError): parse_command(bad)


def test_work_ref_requires_at_least_one_identity_key():
    bad = valid_record_feedback_dict(); bad["work_ref"] = {}
    with pytest.raises(CommandValidationError): parse_command(bad)


def test_operation_id_must_be_canonical_uuid_text():
    bad = valid_record_feedback_dict(); bad["operation_id"] = "not-a-uuid"
    with pytest.raises(CommandValidationError): parse_command(bad)


def test_parse_constructs_typed_commands():
    record = parse_command(valid_record_feedback_dict()); assert isinstance(record, RecordViewingFeedbackCommand); assert record.work_ref.title == "Arrival"; assert record.target_updates[0].rating["score"] == 8.5
    interest = parse_command(valid_set_interest_dict()); assert isinstance(interest, SetInterestCommand); assert interest.state == "shortlist"
    add = parse_command({"schema_version": 1, "operation_id": VALID_UUID, "operation": "add_work", "work_ref": {"title": "Arrival", "year": 2016}}); assert isinstance(add, AddWorkCommand)
    recommend = parse_command({"schema_version": 1, "operation": "recommend_context", "target": "couple", "text": "not dark tonight", "only_unwatched": True, "runtime_max": 120, "include_not_interested": False, "limit": 12}); assert isinstance(recommend, RecommendContextRequest); assert recommend.limit == 12


def test_feedback_term_membership_is_not_checked_by_command_schema():
    data = valid_record_feedback_dict(); data["target_updates"][0]["feedback"] = {"summary": "Specific semantic comment", "signals": [{"term": "nonexistent.future.term", "sentiment": "negative", "strength": 2, "source": "explicit", "confidence": "high"}]}
    command = parse_command(data); assert command.target_updates[0].feedback["signals"][0]["term"] == "nonexistent.future.term"
