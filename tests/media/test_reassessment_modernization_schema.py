from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from media.tools.schema_utils import validate_against_schema


SCHEMA_DIR = Path("media/schemas")
LEDGER_PATH = Path("media/pilots/legacy-reassessment-primary.json")
UUID_A = "123e4567-e89b-42d3-a456-426614174701"
UUID_B = "123e4567-e89b-42d3-a456-426614174702"
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def _ledger_with(modernization: dict) -> dict:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    reviewed_id = next(
        work_id
        for work_id, item in ledger["items"].items()
        if item["status"] == "reviewed"
    )
    doc = deepcopy(ledger)
    doc["items"][reviewed_id]["modernization"] = modernization
    return doc


@pytest.mark.parametrize(
    "modernization",
    [
        {
            "status": "blocked",
            "blocker_code": "provider_identity_ambiguous",
            "recorded_at": "2026-10-07T09:00:00Z",
            "work_digest": DIGEST_A,
        },
        {
            "status": "completed",
            "metadata_operation_id": UUID_A,
            "semantic_operation_id": UUID_B,
            "completed_at": "2026-10-07T09:00:00Z",
            "work_digest": DIGEST_A,
            "vocabulary_digest": DIGEST_B,
        },
    ],
)
def test_pilot_schema_accepts_modernization_marker(modernization: dict) -> None:
    errors = validate_against_schema(
        _ledger_with(modernization),
        "reassessment-pilot.schema.json",
        SCHEMA_DIR,
    )
    assert errors == []


def test_pilot_schema_rejects_extra_modernization_fields() -> None:
    modernization = {
        "status": "blocked",
        "blocker_code": "provider_identity_ambiguous",
        "recorded_at": "2026-10-07T09:00:00Z",
        "work_digest": DIGEST_A,
        "unexpected": True,
    }
    errors = validate_against_schema(
        _ledger_with(modernization),
        "reassessment-pilot.schema.json",
        SCHEMA_DIR,
    )
    assert any("unexpected" in error for error in errors)
