from pathlib import Path

from media.commands.schema import parse_command
from media.tools.build_profiles import build_profile
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


def _write_similarity(root: Path, target="primary") -> None:
    path=root/"media/data/relations/similarity"/f"{target}.yaml"
    path.parent.mkdir(parents=True,exist_ok=True)
    dump_yaml(path,{
        "schema_version":1,
        "target":target,
        "relations":[{
            "type":"similar",
            "left":{"kind":"canonical","work_id":"arrival-2016"},
            "right":{"kind":"canonical","work_id":"unwatched-fit-2020"},
            "terms":["story.intrigue"],
            "note":"Оба держат интригой",
            "updated_at":"2026-10-03T20:00:00+00:00",
            "provenance":{"source":"explicit"},
        }],
    })


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


def test_explicit_similarity_is_separate_taste_evidence_not_affinity(tmp_path):
    root=copy_fixture_repo(tmp_path)
    rebuild_generated(root/"media")
    _write_similarity(root)
    before_affinities=build_profile(root/"media","primary").get("affinities") or {}
    before_files=_file_map(root)

    from media.service.taste_context import build_taste_context
    result=build_taste_context(root/"media",request())

    assert result["similarities"]==[{
        "left":{"kind":"canonical","work_id":"arrival-2016"},
        "right":{"kind":"canonical","work_id":"unwatched-fit-2020"},
        "terms":["story.intrigue"],
        "note":"Оба держат интригой",
        "updated_at":"2026-10-03T20:00:00+00:00",
        "provenance":{"source":"explicit"},
    }]
    assert (build_profile(root/"media","primary").get("affinities") or {})==before_affinities
    assert _file_map(root)==before_files
