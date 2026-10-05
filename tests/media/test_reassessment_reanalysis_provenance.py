from __future__ import annotations

from datetime import datetime, timezone

from media.domain.commands import SetInferredPreferencesCommand
from media.repository.yaml_repo import YamlRepository
from media.service.preferences import plan_set_inferred_preferences
from tests.media.fixture_repo import copy_fixture_repo


UUID = "123e4567-e89b-42d3-a456-426614174020"


def test_set_inferred_preferences_plan_carries_target_for_scheduled_reanalysis_receipt(tmp_path):
    root = copy_fixture_repo(tmp_path)
    plan = plan_set_inferred_preferences(
        YamlRepository(root / "media"),
        SetInferredPreferencesCommand(1, UUID, "primary", ()),
        now=datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
    )

    assert plan.details == {"target": "primary"}
