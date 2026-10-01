from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .common import dump_yaml, iter_yaml_files, load_yaml


@dataclass
class MigrationResult:
    works: list[dict[str, Any]]
    collections: list[dict[str, Any]]


def _viewer_signal(item: Mapping[str, Any]) -> dict[str, Any]:
    signal: dict[str, Any] = {
        "viewing": {"status": item.get("status", "unwatched")},
        "rating": {
            "score": item.get("rating"),
            "source": item.get("rating_source", "none"),
            "confidence": item.get("confidence", "none"),
        },
    }
    comment = item.get("comment")
    if comment:
        signal["feedback"] = {"summary": comment, "signals": []}
    return signal


def migrate_v1_document(doc: Mapping[str, Any], migrated_at: str) -> MigrationResult:
    if doc.get("version") != 1:
        raise ValueError("expected legacy version: 1")
    works: list[dict[str, Any]] = []
    collections: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in doc.get("items", []):
        entity_id = item["id"]
        if entity_id in seen:
            raise ValueError(f"duplicate legacy id: {entity_id}")
        seen.add(entity_id)
        kind = item.get("kind")
        if kind in {"movie", "series"}:
            works.append(
                {
                    "schema_version": 4,
                    "id": entity_id,
                    "entity_type": "work",
                    "identity": {
                        "format": kind,
                        "title_original": item.get("title_original") or item.get("title_ru") or entity_id,
                        "title_ru": item.get("title_ru") or item.get("title_original") or entity_id,
                        "year": item.get("year"),
                    },
                    "viewer_signals": {"primary": _viewer_signal(item)},
                    "provenance": {"created_at": migrated_at, "updated_at": migrated_at},
                }
            )
        elif kind == "collection":
            collections.append(
                {
                    "schema_version": 4,
                    "id": entity_id,
                    "entity_type": "collection",
                    "name_ru": item.get("title_ru") or item.get("title_original") or entity_id,
                    "name_original": item.get("title_original") or item.get("title_ru") or entity_id,
                    "member_ids": [],
                    "viewer_signals": {"primary": _viewer_signal(item)},
                    "provenance": {"created_at": migrated_at, "updated_at": migrated_at},
                }
            )
        else:
            raise ValueError(f"unsupported legacy kind {kind!r} for {entity_id}")
    return MigrationResult(works=works, collections=collections)


def _add_signal(entity: dict[str, Any], term: str, sentiment: str, strength: int, confidence: str = "high") -> None:
    primary = entity.setdefault("viewer_signals", {}).setdefault("primary", {})
    feedback = primary.setdefault("feedback", {"summary": None, "signals": []})
    signals = feedback.setdefault("signals", [])
    if any(s.get("term") == term and s.get("sentiment") == sentiment for s in signals):
        return
    signals.append({"term": term, "sentiment": sentiment, "strength": strength, "source": "inferred", "confidence": confidence})


def _set_partner(entity: dict[str, Any], reaction: str, confidence: str) -> None:
    entity.setdefault("viewer_signals", {})["partner"] = {
        "viewing": {"status": "watched"},
        "reaction": {"value": reaction, "source": "explicit", "confidence": confidence},
    }


def apply_legacy_signal_mappings(result: MigrationResult) -> MigrationResult:
    result = deepcopy(result)
    entities = {e["id"]: e for e in result.works + result.collections}

    structured = {
        "game-night-2018": [
            ("entertainment.engaging", "positive", 2, "high"),
            ("reaction.cringe", "negative", 3, "high"),
            ("humor.absurd", "negative", 2, "high"),
        ],
        "blade-runner-2049-2017": [
            ("visuals.strong", "positive", 2, "high"),
            ("reaction.pacing_dragging", "negative", 2, "high"),
        ],
        "knives-out-2019": [("story.intrigue", "positive", 3, "medium")],
        "sherlock-bbc": [("story.intrigue", "positive", 3, "medium")],
        "oceans-collection": [
            ("characters.charisma", "positive", 2, "medium"),
            ("story.problem_solving", "positive", 2, "medium"),
        ],
        "now-you-see-me-collection": [
            ("characters.charisma", "positive", 2, "medium"),
            ("story.problem_solving", "positive", 2, "medium"),
        ],
        "sherlock-holmes-guy-ritchie-collection": [
            ("characters.charisma", "positive", 2, "medium"),
            ("story.problem_solving", "positive", 2, "medium"),
        ],
    }
    for entity_id, mappings in structured.items():
        entity = entities.get(entity_id)
        if entity:
            for term, sentiment, strength, confidence in mappings:
                _add_signal(entity, term, sentiment, strength, confidence)

    partner = {
        "game-night-2018": ("liked", "high"),
        "grand-budapest-hotel-2014": ("liked", "high"),
        "once-upon-a-time-in-hollywood-2019": ("disliked", "high"),
        "gone-girl-2014": ("liked", "medium"),
    }
    for entity_id, (reaction, confidence) in partner.items():
        entity = entities.get(entity_id)
        if entity:
            _set_partner(entity, reaction, confidence)

    result.works.sort(key=lambda x: x["id"])
    result.collections.sort(key=lambda x: x["id"])
    return result


def write_migration(result: MigrationResult, media_root: Path) -> None:
    works_dir = media_root / "data/works"
    collections_dir = media_root / "data/collections"
    works_dir.mkdir(parents=True, exist_ok=True)
    collections_dir.mkdir(parents=True, exist_ok=True)
    for work in result.works:
        dump_yaml(works_dir / f"{work['id']}.yaml", work)
    for collection in result.collections:
        dump_yaml(collections_dir / f"{collection['id']}.yaml", collection)


def _core_from_v4(entity: Mapping[str, Any]) -> dict[str, Any]:
    primary = (entity.get("viewer_signals") or {}).get("primary") or {}
    rating = primary.get("rating") or {}
    feedback = primary.get("feedback") or {}
    if entity.get("entity_type") == "work":
        ident = entity.get("identity") or {}
        title_ru = ident.get("title_ru")
        title_original = ident.get("title_original")
        year = ident.get("year")
        kind = ident.get("format")
    else:
        title_ru = entity.get("name_ru")
        title_original = entity.get("name_original")
        year = None
        kind = "collection"
    return {
        "id": entity.get("id"), "kind": kind, "title_ru": title_ru, "title_original": title_original,
        "year": year, "status": (primary.get("viewing") or {}).get("status"), "rating": rating.get("score"),
        "rating_source": rating.get("source"), "confidence": rating.get("confidence"), "comment": feedback.get("summary"),
    }


def parity_errors(source_doc: Mapping[str, Any], result: MigrationResult, media_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    source_items = {item["id"]: item for item in source_doc.get("items", [])}
    migrated = {entity["id"]: entity for entity in result.works + result.collections}
    if len(source_items) != len(migrated):
        errors.append(f"count mismatch: source={len(source_items)} migrated={len(migrated)}")
    if set(source_items) != set(migrated):
        errors.append("ID sets differ")
    for entity_id, old in source_items.items():
        new = migrated.get(entity_id)
        if not new:
            continue
        core = _core_from_v4(new)
        for key in ["kind", "title_ru", "title_original", "year", "status", "rating", "rating_source", "confidence", "comment"]:
            if core.get(key) != old.get(key):
                errors.append(f"{entity_id}: {key} {core.get(key)!r} != {old.get(key)!r}")
    if media_root is not None:
        disk: dict[str, dict[str, Any]] = {}
        for d in [media_root / "data/works", media_root / "data/collections"]:
            for path in iter_yaml_files(d):
                doc = load_yaml(path)
                if isinstance(doc, dict) and doc.get("id"):
                    disk[doc["id"]] = doc
        if disk:
            if set(disk) != set(migrated):
                errors.append("destination ID sets differ from migration result")
            for entity_id, expected in migrated.items():
                if entity_id in disk and _core_from_v4(disk[entity_id]) != _core_from_v4(expected):
                    errors.append(f"{entity_id}: destination core fields differ")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy movie data to media v4")
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--migrated-at", default="2026-10-01")
    args = parser.parse_args(argv)

    source = load_yaml(Path(args.source))
    result = apply_legacy_signal_mappings(migrate_v1_document(source, args.migrated_at))
    destination = Path(args.destination)
    errors = parity_errors(source, result, destination if args.check else None)
    if errors:
        for error in errors:
            print(error)
        return 1
    if args.check:
        print(f"OK: {len(result.works)} works + {len(result.collections)} collections = {len(source.get('items', []))} legacy items")
        return 0
    write_migration(result, destination)
    print(f"Wrote {len(result.works)} works and {len(result.collections)} collections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
