from __future__ import annotations

from media.tools.audit_intelligence import collect_intelligence_audit
from media.tools.common import dump_yaml, load_yaml
from tests.media.fixture_repo import copy_fixture_repo


def _set_primary_signal(root, work_id, *, viewing, rating=None, feedback=None):
    path = root / f"media/data/works/{work_id}.yaml"
    work = load_yaml(path)
    signal = {"viewing": {"status": viewing}}
    if rating is not None:
        signal["rating"] = rating
    if feedback is not None:
        signal["feedback"] = feedback
    work.setdefault("viewer_signals", {})["primary"] = signal
    dump_yaml(path, work)


def _add_rated_collection(root):
    path = root / "media/data/collections/audit-rated.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    dump_yaml(
        path,
        {
            "schema_version": 4,
            "id": "audit-rated-collection",
            "entity_type": "collection",
            "name_ru": "Аудит",
            "name_original": "Audit",
            "member_ids": ["arrival-2016"],
            "viewer_signals": {
                "primary": {
                    "viewing": {"status": "watched"},
                    "rating": {
                        "score": 6.5,
                        "source": "inferred",
                        "confidence": "low",
                    },
                    "feedback": {
                        "summary": "structured",
                        "signals": [
                            {
                                "term": "story.intrigue",
                                "sentiment": "positive",
                                "strength": 1,
                                "source": "inferred",
                                "confidence": "low",
                            }
                        ],
                    },
                }
            },
        },
    )


def test_viewing_exposes_watched_count_not_only_status_presence(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _set_primary_signal(
        root,
        "arrival-2016",
        viewing="unwatched",
        feedback={"summary": "placeholder only", "signals": []},
    )
    _set_primary_signal(
        root,
        "unwatched-fit-2020",
        viewing="watched",
        rating={"score": 8.0, "source": "explicit", "confidence": "exact"},
        feedback={"summary": "structured", "signals": []},
    )

    result = collect_intelligence_audit(root)
    works = result["viewing"]["primary"]["works"]

    assert works["watched"]["denominator"] == result["inventory"]["works_total"]
    assert works["watched"]["numerator"] >= 1
    assert works["watched"]["numerator"] < works["numerator"]


def test_rating_sources_are_split_by_works_and_collections(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _set_primary_signal(
        root,
        "unwatched-fit-2020",
        viewing="watched",
        rating={"score": 8.0, "source": "explicit", "confidence": "exact"},
    )
    _add_rated_collection(root)

    result = collect_intelligence_audit(root)
    ratings = result["ratings"]["primary"]

    assert ratings["works"]["by_source"]["explicit"] >= 1
    assert ratings["collections"]["by_source"] == {"inferred": 1}
    assert ratings["entities"]["by_source"]["inferred"] >= 1
    assert "by_source" not in ratings


def test_feedback_coverage_uses_structured_signals_and_exposes_rated_subset(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _set_primary_signal(
        root,
        "arrival-2016",
        viewing="unwatched",
        feedback={"summary": "migration placeholder", "signals": []},
    )
    _set_primary_signal(
        root,
        "unwatched-fit-2020",
        viewing="watched",
        rating={"score": 8.0, "source": "explicit", "confidence": "exact"},
        feedback={
            "summary": "meaningful structured feedback",
            "signals": [
                {
                    "term": "story.intrigue",
                    "sentiment": "positive",
                    "strength": 2,
                    "source": "explicit",
                    "confidence": "high",
                }
            ],
        },
    )

    result = collect_intelligence_audit(root)
    feedback = result["feedback"]["primary"]["works"]
    ratings = result["ratings"]["primary"]["works"]

    assert feedback["numerator"] >= 1
    assert feedback["numerator"] < result["inventory"]["works_total"]
    assert feedback["rated"]["denominator"] == ratings["numerator"]
    assert feedback["rated"]["numerator"] <= feedback["numerator"]
    assert feedback["rated"]["numerator"] >= 1


def test_rating_metrics_expose_mean_score_per_entity_class(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _set_primary_signal(
        root,
        "unwatched-fit-2020",
        viewing="watched",
        rating={"score": 8.0, "source": "explicit", "confidence": "exact"},
    )
    _add_rated_collection(root)

    result = collect_intelligence_audit(root)
    ratings = result["ratings"]["primary"]

    assert isinstance(ratings["works"]["mean_score"], float)
    assert ratings["collections"]["mean_score"] == 6.5
    assert isinstance(ratings["entities"]["mean_score"], float)
