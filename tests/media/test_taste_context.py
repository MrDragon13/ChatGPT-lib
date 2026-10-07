from pathlib import Path

from media.commands.schema import parse_command
from media.tools.build_profiles import build_profile
from media.tools.common import dump_yaml, load_yaml
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import append_material_rating_event, copy_fixture_repo


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


def _write_trait_rating_work(
    root: Path,
    work_id: str,
    *,
    term: str,
    primary_rating: float | None,
    partner_rating: float | None,
    trait_confidence: str = "high",
) -> None:
    work = {
        "schema_version":4,
        "entity_type":"work",
        "id":work_id,
        "identity":{"format":"movie","title_original":work_id,"title_ru":work_id,"year":2026},
        "metadata":{
            "external":{"runtime_min":100},
            "semantic":{"traits":[{"term":term,"source":"llm_inferred","confidence":trait_confidence}]},
        },
        "viewer_signals":{},
    }
    for target, rating in (("primary", primary_rating), ("partner", partner_rating)):
        if rating is None:
            continue
        work["viewer_signals"][target] = {
            "viewing":{"status":"watched"},
            "rating":{"score":rating,"source":"explicit","confidence":"exact"},
        }
    dump_yaml(root/f"media/data/works/{work_id}.yaml", work)


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
    assert "term_signals" in result["couple"]


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


def test_couple_term_signals_expose_member_directions_without_changing_aggregation(tmp_path):
    root=copy_fixture_repo(tmp_path)
    _write_trait_rating_work(root,"term-agreement",term="story.intrigue",primary_rating=9.0,partner_rating=8.0)
    _write_trait_rating_work(root,"term-disagreement",term="pacing.slow",primary_rating=9.0,partner_rating=2.0)
    _write_trait_rating_work(root,"term-insufficient",term="visuals.strong",primary_rating=9.0,partner_rating=None)
    _write_trait_rating_work(root,"term-low-confidence",term="tone.dark",primary_rating=9.0,partner_rating=8.0,trait_confidence="low")
    rebuild_generated(root/"media")
    before_profile=build_profile(root/"media","couple")
    before_files=_file_map(root)

    from media.service.taste_context import build_taste_context
    result=build_taste_context(root/"media",request(target="couple",representative_limit=20))

    rows=result["couple"]["term_signals"]
    assert [row["term"] for row in rows]==sorted(row["term"] for row in rows)
    by_term={row["term"]:row for row in rows}

    agreement=by_term["story.intrigue"]
    assert agreement["status"]=="agreement"
    assert agreement["members"]["primary"]["direction"]=="positive"
    assert agreement["members"]["partner"]["direction"]=="positive"

    disagreement=by_term["pacing.slow"]
    assert disagreement["status"]=="disagreement"
    assert disagreement["members"]["primary"]["direction"]=="positive"
    assert disagreement["members"]["partner"]["direction"]=="negative"

    insufficient=by_term["visuals.strong"]
    assert insufficient["status"]=="insufficient"
    assert insufficient["members"]["primary"]["direction"]=="positive"
    assert insufficient["members"]["partner"]["direction"] is None

    low_confidence=by_term["tone.dark"]
    assert low_confidence["status"]=="agreement"
    assert low_confidence["members"]["primary"]["direction"]=="positive"
    assert low_confidence["members"]["primary"]["confidence"]=="low"

    assert result["limitations"]==["couple_term_disagreement"]
    assert build_profile(root/"media","couple")==before_profile
    assert _file_map(root)==before_files


def test_taste_context_exposes_due_reanalysis_gate(tmp_path):
    root=copy_fixture_repo(tmp_path)
    for index in range(5):
        append_material_rating_event(
            root,
            score=7.0 + index / 2,
            event_id=f"123e4567-e89b-42d3-a456-4266141745{index:02d}",
            at=f"2026-10-07T12:0{index}:00Z",
        )
    rebuild_generated(root/"media")
    from media.service.taste_context import build_taste_context
    result=build_taste_context(root/"media",request("primary"))
    assert result["reanalysis"]["target"]=="primary"
    assert result["reanalysis"]["due"] is True
    assert result["reanalysis"]["outstanding_count"]==5
    assert "taste_reanalysis_due" in result["limitations"]


def test_couple_taste_context_exposes_member_reanalysis_statuses(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/"media")
    for index in range(5):
        append_material_rating_event(
            root,
            target="partner",
            score=6.0 + index / 2,
            event_id=f"123e4567-e89b-42d3-a456-4266141746{index:02d}",
            at=f"2026-10-07T13:0{index}:00Z",
        )
    rebuild_generated(root/"media")
    from media.service.taste_context import build_taste_context
    result=build_taste_context(root/"media",request("couple"))
    assert result["reanalysis"]["due"] is True
    assert set(result["reanalysis"]["members"])=={"primary","partner"}
    assert result["reanalysis"]["members"]["partner"]["due"] is True
    assert "outstanding_count" not in result["reanalysis"]
