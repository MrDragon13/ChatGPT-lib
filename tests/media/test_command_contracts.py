from __future__ import annotations

import pytest

from media.commands.schema import parse_command
from media.domain.errors import CommandValidationError
from media.domain.commands import AddWorkCommand, RecommendContextRequest, RecordViewingFeedbackCommand, SetInterestCommand

VALID_UUID = "123e4567-e89b-42d3-a456-426614174000"
SESSION_UUID = "123e4567-e89b-42d3-a456-426614174001"
REANALYSIS_UUID = "123e4567-e89b-42d3-a456-426614174002"
LEDGER_DIGEST = "sha256:" + "a" * 64
WORK_DIGEST = "sha256:" + "b" * 64
VOCABULARY_DIGEST = "sha256:" + "c" * 64
METADATA_UUID = "123e4567-e89b-42d3-a456-426614174003"
SEMANTIC_UUID = "123e4567-e89b-42d3-a456-426614174004"


def valid_record_feedback_dict() -> dict:
    return {"schema_version": 1, "operation_id": VALID_UUID, "operation": "record_viewing_feedback", "work_ref": {"title": "Arrival", "year": 2016}, "target_updates": [{"target": "primary", "viewing": {"status": "watched"}, "rating": {"score": 8.5, "source": "explicit_approx", "confidence": "high"}}]}


def valid_set_interest_dict(priority: int | None = 3) -> dict:
    return {"schema_version": 1, "operation_id": VALID_UUID, "operation": "set_interest", "work_ref": {"id": "arrival-2016"}, "target": "primary", "state": "shortlist", "priority": priority}


def valid_refresh_metadata_dict() -> dict:
    return {"schema_version": 1, "operation_id": VALID_UUID, "operation": "refresh_metadata", "scope": "all_movies"}


def valid_reserve_reassessment_dict() -> dict:
    return {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "reserve_reassessment_session",
        "pilot_id": "primary-legacy-v1",
        "session_id": SESSION_UUID,
        "work_ids": ["arrival-2016", "batman-2022"],
        "expected_ledger_digest": LEDGER_DIGEST,
    }


def valid_complete_reassessment_dict(outcome: str = "changed") -> dict:
    data = {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "complete_reassessment_item",
        "pilot_id": "primary-legacy-v1",
        "session_id": SESSION_UUID,
        "work_id": "arrival-2016",
        "expected_ledger_digest": LEDGER_DIGEST,
        "outcome": outcome,
    }
    if outcome == "changed":
        data["historical_exposure"] = {"timing": "none", "before_finalization": True}
        data["feedback_edit"] = {
            "set": {"rating": {"score": 8.5, "source": "explicit", "confidence": "exact"}},
            "clear": ["feedback"],
        }
    elif outcome == "confirmed_unchanged":
        data["historical_exposure"] = {"timing": "after_initial_response", "before_finalization": True}
    return data


def valid_close_reassessment_dict() -> dict:
    return {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "close_reassessment_session",
        "pilot_id": "primary-legacy-v1",
        "session_id": SESSION_UUID,
        "expected_ledger_digest": LEDGER_DIGEST,
        "scheduled_reanalysis_operation_id": REANALYSIS_UUID,
    }


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
    assert command.year_overrides == {}


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


def test_refresh_metadata_year_override_is_typed_and_bounded():
    data = valid_refresh_metadata_dict(); data["year_overrides"] = {"gentlemen-2019": 2020}
    command = parse_command(data)
    assert command.year_overrides == {"gentlemen-2019": 2020}
    bad = valid_refresh_metadata_dict(); bad["year_overrides"] = {"gentlemen-2019": 1879}
    with pytest.raises(CommandValidationError): parse_command(bad)


def test_edit_viewing_feedback_command_supports_explicit_set_clear_and_purge():
    data = {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "edit_viewing_feedback",
        "work_ref": {"id": "arrival-2016"},
        "target_edits": [{
            "target": "primary",
            "set": {"rating": {"score": 9.0, "source": "explicit", "confidence": "exact"}},
            "clear": ["feedback"],
            "purge": False,
        }],
    }
    command = parse_command(data)
    assert type(command).__name__ == "EditViewingFeedbackCommand"
    assert command.target_edits[0].target == "primary"
    assert command.target_edits[0].set_values["rating"]["score"] == 9.0
    assert command.target_edits[0].clear == ("feedback",)
    assert command.target_edits[0].purge is False


def test_edit_viewing_feedback_rejects_implicit_or_unknown_clear_components():
    bad = {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "edit_viewing_feedback",
        "work_ref": {"id": "arrival-2016"},
        "target_edits": [{"target": "primary", "clear": ["everything"]}],
    }
    with pytest.raises(CommandValidationError):
        parse_command(bad)


def test_set_inferred_preferences_command_carries_evidence_backed_replacement():
    data = {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "set_inferred_preferences",
        "target": "primary",
        "hypotheses": [{
            "id": "intrigue-problem-solving",
            "statement": "Высокие оценки повторяются у фильмов с интригой и решением задач.",
            "affinity": 0.8,
            "confidence": "medium",
            "terms": ["story.intrigue", "story.problem_solving"],
            "evidence": [
                {"entity_id": "arrival-2016", "kind": "rating_correlation"},
                {"entity_id": "knives-out-2019", "kind": "explicit_feedback"},
            ],
        }],
    }
    command = parse_command(data)
    assert type(command).__name__ == "SetInferredPreferencesCommand"
    assert command.target == "primary"
    assert command.hypotheses[0]["affinity"] == 0.8
    assert command.hypotheses[0]["confidence"] == "medium"
    assert command.hypotheses[0]["evidence"][0]["entity_id"] == "arrival-2016"


def test_set_semantic_fingerprint_command_is_typed_and_strict():
    data = {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "set_semantic_fingerprint",
        "work_ref": {"id": "arrival-2016"},
        "traits": [
            {"term": "story.intrigue", "source": "llm_inferred", "confidence": "high"},
            {"term": "pacing.slow", "source": "external_source", "confidence": "medium"},
        ],
    }
    command = parse_command(data)
    assert type(command).__name__ == "SetSemanticFingerprintCommand"
    assert command.traits[0]["term"] == "story.intrigue"
    bad = dict(data); bad["unexpected"] = True
    with pytest.raises(CommandValidationError):
        parse_command(bad)


def test_record_recommendation_interaction_command_preserves_ephemeral_event_type():
    data = {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "record_recommendation_interaction",
        "session_id": "evening-2026-10-03",
        "target": "couple",
        "work_ref": {"title": "The Invitation", "year": 2015},
        "event": "not_tonight",
        "note": "Хочется чего-то полегче.",
    }
    command = parse_command(data)
    assert type(command).__name__ == "RecordRecommendationInteractionCommand"
    assert command.event == "not_tonight"
    assert command.work_ref.title == "The Invitation"


def test_reassessment_commands_parse_to_narrow_typed_contracts():
    reserve = parse_command(valid_reserve_reassessment_dict())
    assert type(reserve).__name__ == "ReserveReassessmentSessionCommand"
    assert reserve.work_ids == ("arrival-2016", "batman-2022")

    complete = parse_command(valid_complete_reassessment_dict())
    assert type(complete).__name__ == "CompleteReassessmentItemCommand"
    assert complete.outcome == "changed"
    assert complete.feedback_edit["clear"] == ["feedback"]

    close = parse_command(valid_close_reassessment_dict())
    assert type(close).__name__ == "CloseReassessmentSessionCommand"
    assert close.scheduled_reanalysis_operation_id == REANALYSIS_UUID


def test_reserve_reassessment_enforces_uuid_digest_and_batch_size():
    for key in ("operation_id", "session_id"):
        bad = valid_reserve_reassessment_dict(); bad[key] = "not-a-uuid"
        with pytest.raises(CommandValidationError): parse_command(bad)
    bad = valid_reserve_reassessment_dict(); bad["expected_ledger_digest"] = "sha256:nope"
    with pytest.raises(CommandValidationError): parse_command(bad)
    for work_ids in ([], ["arrival-2016"] * 2, [f"work-{index}" for index in range(6)]):
        bad = valid_reserve_reassessment_dict(); bad["work_ids"] = work_ids
        with pytest.raises(CommandValidationError): parse_command(bad)


def test_reassessment_commands_reject_unknown_pilot_id():
    for factory in (valid_reserve_reassessment_dict, valid_complete_reassessment_dict, valid_close_reassessment_dict):
        bad = factory(); bad["pilot_id"] = "partner-legacy-v1"
        with pytest.raises(CommandValidationError): parse_command(bad)


def test_complete_reassessment_outcome_controls_feedback_and_history_fields():
    bad = valid_complete_reassessment_dict("changed"); bad.pop("feedback_edit")
    with pytest.raises(CommandValidationError): parse_command(bad)

    for outcome in ("confirmed_unchanged", "deferred"):
        bad = valid_complete_reassessment_dict(outcome)
        bad["feedback_edit"] = {"clear": ["feedback"]}
        with pytest.raises(CommandValidationError): parse_command(bad)

    deferred = valid_complete_reassessment_dict("deferred")
    deferred["historical_exposure"] = {"timing": "none", "before_finalization": True}
    with pytest.raises(CommandValidationError): parse_command(deferred)


def test_complete_reassessment_edit_forbids_target_purge_and_unknown_components():
    for edit in (
        {"target": "primary", "clear": ["feedback"]},
        {"purge": True},
        {"clear": ["everything"]},
    ):
        bad = valid_complete_reassessment_dict("changed"); bad["feedback_edit"] = edit
        with pytest.raises(CommandValidationError): parse_command(bad)


def test_reassessment_session_ids_and_optional_reanalysis_id_are_canonical_uuids():
    bad = valid_complete_reassessment_dict(); bad["session_id"] = "123E4567-E89B-42D3-A456-426614174001"
    with pytest.raises(CommandValidationError): parse_command(bad)
    bad = valid_close_reassessment_dict(); bad["scheduled_reanalysis_operation_id"] = "not-a-uuid"
    with pytest.raises(CommandValidationError): parse_command(bad)


def valid_refresh_work_metadata_dict() -> dict:
    return {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "refresh_work_metadata",
        "work_ref": {"id": "arrival-2016"},
        "expected_work_digest": WORK_DIGEST,
    }


def valid_record_modernization_dict(outcome: str = "completed") -> dict:
    data = {
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "record_reassessment_modernization",
        "pilot_id": "primary-legacy-v1",
        "work_id": "arrival-2016",
        "outcome": outcome,
        "expected_ledger_digest": LEDGER_DIGEST,
        "expected_work_digest": WORK_DIGEST,
    }
    if outcome == "completed":
        data.update({
            "metadata_operation_id": METADATA_UUID,
            "semantic_operation_id": SEMANTIC_UUID,
            "vocabulary_digest": VOCABULARY_DIGEST,
        })
    else:
        data["blocker_code"] = "provider_identity_ambiguous"
    return data


def test_refresh_work_metadata_requires_one_work_and_digest():
    command = parse_command(valid_refresh_work_metadata_dict())
    assert type(command).__name__ == "RefreshWorkMetadataCommand"
    assert command.work_ref.id == "arrival-2016"
    assert command.expected_work_digest == WORK_DIGEST

    bad = valid_refresh_work_metadata_dict(); bad["expected_work_digest"] = "sha256:nope"
    with pytest.raises(CommandValidationError):
        parse_command(bad)
    bad = valid_refresh_work_metadata_dict(); bad["unexpected"] = True
    with pytest.raises(CommandValidationError):
        parse_command(bad)


def test_reassessment_modernization_completed_and_blocked_variants_are_typed():
    completed = parse_command(valid_record_modernization_dict("completed"))
    assert type(completed).__name__ == "RecordReassessmentModernizationCommand"
    assert completed.outcome == "completed"
    assert completed.metadata_operation_id == METADATA_UUID
    assert completed.semantic_operation_id == SEMANTIC_UUID
    assert completed.vocabulary_digest == VOCABULARY_DIGEST
    assert completed.blocker_code is None

    blocked = parse_command(valid_record_modernization_dict("blocked"))
    assert blocked.outcome == "blocked"
    assert blocked.blocker_code == "provider_identity_ambiguous"
    assert blocked.metadata_operation_id is None


def test_reassessment_modernization_variant_fields_are_strict():
    bad = valid_record_modernization_dict("completed"); bad.pop("semantic_operation_id")
    with pytest.raises(CommandValidationError):
        parse_command(bad)
    bad = valid_record_modernization_dict("completed"); bad["blocker_code"] = "provider_identity_conflict"
    with pytest.raises(CommandValidationError):
        parse_command(bad)
    bad = valid_record_modernization_dict("blocked"); bad["metadata_operation_id"] = METADATA_UUID
    with pytest.raises(CommandValidationError):
        parse_command(bad)
    bad = valid_record_modernization_dict("blocked"); bad["blocker_code"] = "whatever"
    with pytest.raises(CommandValidationError):
        parse_command(bad)


def test_modernization_operation_ids_are_canonical_lowercase_uuids():
    bad = valid_refresh_work_metadata_dict(); bad["operation_id"] = "NOT-A-UUID"
    with pytest.raises(CommandValidationError):
        parse_command(bad)
    for key in ("metadata_operation_id", "semantic_operation_id"):
        bad = valid_record_modernization_dict("completed"); bad[key] = "not-a-uuid"
        with pytest.raises(CommandValidationError):
            parse_command(bad)


def valid_record_media_entry_dict(create_if_missing: bool = False) -> dict:
    data = {
        "schema_version": 1,
        "operation_id": "123e4567-e89b-42d3-a456-426614174301",
        "idempotency_key": "123e4567-e89b-42d3-a456-426614174399",
        "operation": "record_media_entry",
        "work_ref": {"id": "arrival-2016"},
        "create_if_missing": create_if_missing,
        "target_updates": [{"target": "primary", "viewing": {"status": "watched"}}],
        "preconditions": {"expected_viewer_digests": {"primary": "sha256:" + "1" * 64}},
    }
    if create_if_missing:
        data["work_ref"] = {"tmdb_media_type": "movie", "tmdb_id": 329865}
        data["creation_context"] = {
            "resolved_identity": {
                "format": "movie",
                "title_original": "Arrival",
                "title_ru": "Прибытие",
                "year": 2016,
                "external_ids": {"tmdb": {"media_type": "movie", "id": 329865}},
            },
            "provider_identity": {"media_type": "movie", "id": 329865},
            "minimum_metadata": {"runtime_min": 116},
        }
        data["semantic_snapshot"] = {
            "traits": [{"term": "story.intrigue", "source": "llm_inferred", "confidence": "high"}],
            "semantic_input_digest": "sha256:" + "2" * 64,
            "vocabulary_digest": "sha256:" + "3" * 64,
            "algorithm_version": "media-semantic-v1",
        }
        data["preconditions"] = {"expected_viewer_digests": {}}
    return data


def test_record_media_entry_parses_existing_and_new_work_variants():
    existing = parse_command(valid_record_media_entry_dict())
    assert type(existing).__name__ == "RecordMediaEntryCommand"
    assert existing.idempotency_key.endswith("4399")
    assert existing.preconditions.expected_viewer_digests["primary"].startswith("sha256:")

    created = parse_command(valid_record_media_entry_dict(create_if_missing=True))
    assert created.create_if_missing is True
    assert created.creation_context.provider_identity.id == 329865
    assert created.semantic_snapshot.algorithm_version == "media-semantic-v1"


def test_record_media_entry_requires_creation_and_semantics_only_for_creation():
    for missing in ("creation_context", "semantic_snapshot"):
        bad = valid_record_media_entry_dict(create_if_missing=True)
        bad.pop(missing)
        with pytest.raises(CommandValidationError):
            parse_command(bad)

    bad = valid_record_media_entry_dict()
    bad["creation_context"] = valid_record_media_entry_dict(True)["creation_context"]
    with pytest.raises(CommandValidationError):
        parse_command(bad)


def test_record_media_entry_existing_work_requires_digest_for_each_target():
    bad = valid_record_media_entry_dict()
    bad["preconditions"]["expected_viewer_digests"] = {}
    with pytest.raises(CommandValidationError, match="expected viewer digest"):
        parse_command(bad)


def test_record_media_entry_operation_and_idempotency_ids_are_canonical_uuid_text():
    for key in ("operation_id", "idempotency_key"):
        bad = valid_record_media_entry_dict()
        bad[key] = "NOT-A-UUID"
        with pytest.raises(CommandValidationError):
            parse_command(bad)


def test_record_media_entry_rejects_unknown_fields():
    bad = valid_record_media_entry_dict()
    bad["unexpected"] = True
    with pytest.raises(CommandValidationError):
        parse_command(bad)
