from pathlib import Path

from media.tools.migrate_v1 import apply_legacy_signal_mappings, migrate_v1_document, write_migration


def sample_doc():
    return {
        "version": 1,
        "rating_scale": 10,
        "items": [
            {"id":"game-night-2018","kind":"movie","title_ru":"Игра в ночь","title_original":"Game Night","year":2018,"status":"watched","rating":7.0,"rating_source":"explicit","confidence":"high","comment":"Интересный, но кринж и абсурд."},
            {"id":"sherlock-bbc","kind":"series","title_ru":"Шерлок","title_original":"Sherlock","year":2010,"status":"watched","rating":9.5,"rating_source":"inferred","confidence":"high","comment":"Топ."},
            {"id":"oceans-collection","kind":"collection","title_ru":"Ocean’s","title_original":"Ocean's collection","year":None,"status":"watched","rating":8.5,"rating_source":"inferred","confidence":"medium","comment":"Вся серия хорошая."},
            {"id":"arrival-2016","kind":"movie","title_ru":"Прибытие","title_original":"Arrival","year":2016,"status":"unwatched","rating":None,"rating_source":"none","confidence":"none","comment":"Не смотрел."},
        ],
    }


def by_id(result):
    return {x["id"]: x for x in result.works + result.collections}


def test_one_to_one_migration_preserves_core_fields_without_guessing():
    source = sample_doc()
    result = migrate_v1_document(source, "2026-10-01")
    assert len(result.works) + len(result.collections) == len(source["items"])
    mapped = by_id(result)
    assert set(mapped) == {x["id"] for x in source["items"]}
    work = mapped["game-night-2018"]
    assert work["identity"] == {"format":"movie","title_original":"Game Night","title_ru":"Игра в ночь","year":2018}
    assert work["viewer_signals"]["primary"]["viewing"]["status"] == "watched"
    assert work["viewer_signals"]["primary"]["rating"] == {"score":7.0,"source":"explicit","confidence":"high"}
    assert work["viewer_signals"]["primary"]["feedback"]["summary"] == source["items"][0]["comment"]
    assert "medium" not in work["identity"] and "external_ids" not in work["identity"] and "seasons" not in work


def test_unwatched_does_not_synthesize_negative_reaction():
    result = migrate_v1_document(sample_doc(), "2026-10-01")
    arrival = by_id(result)["arrival-2016"]
    primary = arrival["viewer_signals"]["primary"]
    assert primary["viewing"]["status"] == "unwatched"
    assert "reaction" not in primary
    assert primary["rating"] == {"score":None,"source":"none","confidence":"none"}


def test_collection_rating_stays_on_collection_and_members_are_empty():
    result = migrate_v1_document(sample_doc(), "2026-10-01")
    collection = by_id(result)["oceans-collection"]
    assert collection["entity_type"] == "collection"
    assert collection["member_ids"] == []
    assert collection["viewer_signals"]["primary"]["rating"]["score"] == 8.5
    assert all(w["id"] != "oceans-collection" for w in result.works)


def test_legacy_structured_signals_are_inferred_and_partner_fact_is_sparse():
    result = apply_legacy_signal_mappings(migrate_v1_document(sample_doc(), "2026-10-01"))
    game = by_id(result)["game-night-2018"]
    signals = game["viewer_signals"]["primary"]["feedback"]["signals"]
    assert {(s["term"], s["sentiment"]) for s in signals} >= {("entertainment.engaging","positive"),("reaction.cringe","negative"),("humor.absurd","negative")}
    assert {s["source"] for s in signals} == {"inferred"}
    partner = game["viewer_signals"]["partner"]
    assert partner["viewing"]["status"] == "watched"
    assert partner["reaction"] == {"value":"liked","source":"explicit","confidence":"high"}
    assert "rating" not in partner
    assert "group_signals" not in game


def test_write_migration_creates_one_yaml_per_entity(tmp_path: Path):
    result = apply_legacy_signal_mappings(migrate_v1_document(sample_doc(), "2026-10-01"))
    write_migration(result, tmp_path / "media")
    assert sorted(p.stem for p in (tmp_path/"media/data/works").glob("*.yaml")) == ["arrival-2016","game-night-2018","sherlock-bbc"]
    assert sorted(p.stem for p in (tmp_path/"media/data/collections").glob("*.yaml")) == ["oceans-collection"]
