from pathlib import Path

from media.commands.schema import parse_command
from media.tools.common import dump_yaml, load_yaml
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo


def request(target="primary", recent_limit=3, representative_limit=3):
    return parse_command({
        "schema_version": 1,
        "operation": "taste_context",
        "target": target,
        "recent_limit": recent_limit,
        "representative_limit": representative_limit,
    })


def _file_map(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_taste_context_is_read_only_and_compact_for_primary(tmp_path):
    root = copy_fixture_repo(tmp_path)
    rebuild_generated(root / "media")
    inferred = root / "media/preferences/inferred"
    inferred.mkdir(parents=True, exist_ok=True)
    dump_yaml(inferred / "primary.yaml", {
        "schema_version":1,
        "target":"primary",
        "updated_at":"2026-10-03T00:00:00Z",
        "hypotheses":[{
            "id":"intrigue-pattern",
            "statement":"Повторяется любовь к интриге.",
            "affinity":0.8,
            "confidence":"medium",
            "terms":["story.intrigue"],
            "evidence":[{"entity_id":"arrival-2016","kind":"rating_correlation"}],
        }],
    })
    before = _file_map(root)
    from media.service.taste_context import build_taste_context
    result = build_taste_context(root / "media", request())
    after = _file_map(root)
    assert result["target"] == "primary"
    assert result["profile"]["inferred_preferences"][0]["id"] == "intrigue-pattern"
    assert "strongest_affinities" in result["profile"]
    assert set(result["representative"]) == {"high", "low"}
    assert "arrival-2016" in result["exclusions"]["watched"]
    assert before == after


def test_taste_context_missing_inferred_preferences_is_normal(tmp_path):
    root = copy_fixture_repo(tmp_path)
    rebuild_generated(root / "media")
    from media.service.taste_context import build_taste_context
    result = build_taste_context(root / "media", request())
    assert result["profile"]["inferred_preferences"] == []


def test_couple_context_exposes_disagreement_without_hidden_average(tmp_path):
    root = copy_fixture_repo(tmp_path)
    work_path = root / "media/data/works/arrival-2016.yaml"
    work = load_yaml(work_path)
    work.setdefault("viewer_signals", {}).setdefault("primary", {}).update({
        "viewing":{"status":"watched"},
        "rating":{"score":9.0,"source":"explicit","confidence":"exact"},
    })
    work["viewer_signals"].setdefault("partner", {}).update({
        "viewing":{"status":"watched"},
        "rating":{"score":4.0,"source":"explicit","confidence":"exact"},
    })
    dump_yaml(work_path, work)
    rebuild_generated(root / "media")
    from media.service.taste_context import build_taste_context
    result = build_taste_context(root / "media", request(target="couple"))
    row = next(item for item in result["couple"]["disagreements"] if item["id"] == "arrival-2016")
    assert row["ratings"] == {"partner":4.0,"primary":9.0}
    assert "score" not in row
    assert "arrival-2016" in result["exclusions"]["watched"]


def test_taste_context_respects_representative_and_recent_limits(tmp_path):
    root = copy_fixture_repo(tmp_path)
    rebuild_generated(root / "media")
    from media.service.taste_context import build_taste_context
    result = build_taste_context(root / "media", request(recent_limit=1, representative_limit=1))
    assert len(result["representative"]["high"]) <= 1
    assert len(result["representative"]["low"]) <= 1
    assert len(result["recent_feedback"]) <= 1
