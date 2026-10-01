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


def valid_refresh_metadata_dict() -> dict:
    return {"schema_version": 1, "operation_id": VALID_UUID, "operation": "refresh_metadata", "scope": "all_movies"}


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


def test_record_feedback_create_if_missing_is_typed_and_defaults_false():
    default = parse_command(valid_record_feedback_dict())
    assert isinstance(default, RecordViewingFeedbackCommand)
    assert default.create_if_missing is False
    data = valid_record_feedback_dict(); data["create_if_missing"] = True
    command = parse_command(data)
    assert command.create_if_missing is True


def test_feedback_term_membership_is_not_checked_by_command_schema():
    data = valid_record_feedback_dict(); data["target_updates"][0]["feedback"] = {"summary": "Specific semantic comment", "signals": [{"term": "nonexistent.future.term", "sentiment": "negative", "strength": 2, "source": "explicit", "confidence": "high"}]}
    command = parse_command(data); assert command.target_updates[0].feedback["signals"][0]["term"] == "nonexistent.future.term"


def test_refresh_metadata_minimal_command_is_typed():
    command = parse_command(valid_refresh_metadata_dict())
    assert type(command).__name__ == "RefreshMetadataCommand"
    assert command.scope == "all_movies"
    assert command.tmdb_overrides == {}


def test_refresh_metadata_is_strict_and_all_movies_only():
    bad = valid_refresh_metadata_dict(); bad["scope"] = "all_works"
    with pytest.raises(CommandValidationError): parse_command(bad)
    bad = valid_refresh_metadata_dict(); bad["unexpected"] = True
    with pytest.raises(CommandValidationError): parse_command(bad)


def test_refresh_metadata_operation_id_is_canonical_uuid():
    bad = valid_refresh_metadata_dict(); bad["operation_id"] = "NOT-A-UUID"
    with pytest.raises(CommandValidationError): parse_command(bad)


def test_refresh_metadata_override_requires_movie_and_positive_tmdb_id():
    data = valid_refresh_metadata_dict(); data["tmdb_overrides"] = {"arrival-2016": {"media_type": "movie", "id": 329865}}
    command = parse_command(data)
    assert command.tmdb_overrides["arrival-2016"].media_type == "movie"
    assert command.tmdb_overrides["arrival-2016"].id == 329865
    bad = valid_refresh_metadata_dict(); bad["tmdb_overrides"] = {"arrival-2016": {"media_type": "tv", "id": 329865}}
    with pytest.raises(CommandValidationError): parse_command(bad)
    bad = valid_refresh_metadata_dict(); bad["tmdb_overrides"] = {"arrival-2016": {"media_type": "movie", "id": 0}}
    with pytest.raises(CommandValidationError): parse_command(bad)
