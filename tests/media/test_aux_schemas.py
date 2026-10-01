from pathlib import Path

from media.tools.schema_utils import validate_against_schema

SCHEMAS = Path("media/schemas")


def assert_valid(instance, schema):
    assert validate_against_schema(instance, schema, SCHEMAS) == []


def assert_invalid(instance, schema):
    assert validate_against_schema(instance, schema, SCHEMAS)


def test_viewers_are_anonymous_closed_records():
    doc = {"schema_version": 4, "viewers": {"primary": {}, "partner": {}}}
    assert_valid(doc, "viewers.schema.json")
    assert_invalid({"schema_version": 4, "viewers": {"primary": {"name": "Max"}}}, "viewers.schema.json")


def test_group_contains_stable_viewer_ids_and_is_closed():
    doc = {"schema_version": 4, "groups": {"couple": {"members": ["primary", "partner"]}}}
    assert_valid(doc, "groups.schema.json")
    assert_invalid({"schema_version": 4, "groups": {"couple": {"members": ["primary"], "label": "Us"}}}, "groups.schema.json")


def test_vocabulary_requires_namespaced_canonical_term_shape():
    doc = {"schema_version": 4, "terms": {"story.intrigue": {"kind": "aspect", "label_ru": "Интрига", "definition": "Желание узнать что будет дальше.", "parent": "story", "aliases": ["сюжетная интрига"]}}}
    assert_valid(doc, "vocabulary.schema.json")
    broken = {"schema_version": 4, "terms": {"intrigue": {"kind": "aspect", "label_ru": "Интрига", "definition": "x", "aliases": []}}}
    assert_invalid(broken, "vocabulary.schema.json")


def test_list_shape_is_closed_and_targeted():
    doc = {"schema_version": 4, "id": "weekend", "entity_type": "list", "target": "couple", "title": "На выходные", "description": None, "member_ids": []}
    assert_valid(doc, "list.schema.json")
    assert_invalid({**doc, "extra": True}, "list.schema.json")


def test_interaction_type_enum_and_conditional_list_id():
    base = {"schema_version": 4, "id": "evt-1", "entity_type": "interaction", "at": "2026-10-01T20:15:00+02:00", "target": "couple", "work_id": "arrival-2016"}
    assert_valid({**base, "type": "recommended"}, "interaction.schema.json")
    assert_invalid({**base, "type": "invented"}, "interaction.schema.json")
    assert_invalid({**base, "type": "added_to_list"}, "interaction.schema.json")
    assert_valid({**base, "type": "added_to_list", "list_id": "weekend"}, "interaction.schema.json")


def test_tombstone_shape_is_closed():
    doc = {"schema_version": 4, "id": "old-id", "entity_type": "tombstone", "status": "merged", "redirect_to": "new-id"}
    assert_valid(doc, "tombstone.schema.json")
    assert_invalid({**doc, "status": "deleted"}, "tombstone.schema.json")


def test_explicit_preference_rule_constraint_provenance():
    doc = {"schema_version": 4, "target": "primary", "preferences": [{"id": "genre-secondary", "statement": "Genre is secondary.", "source": "explicit", "confidence": "exact"}], "rules": [{"id": "slow-context", "statement": "Slow is okay when justified.", "source": "explicit", "confidence": "exact"}], "constraints": []}
    assert_valid(doc, "explicit-preferences.schema.json")
    bad = {**doc, "preferences": [{"id": "x", "statement": "x", "source": "inferred", "confidence": "high"}]}
    assert_invalid(bad, "explicit-preferences.schema.json")
