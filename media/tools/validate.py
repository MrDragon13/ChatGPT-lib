from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from media.service.reassessment_validation import validate_reassessment_snapshot

from .common import iter_jsonl, iter_yaml_files, load_yaml
from .schema_utils import validate_against_schema


@dataclass(frozen=True, order=True)
class ValidationIssue:
    path: str
    code: str
    message: str


def _issue(issues: list[ValidationIssue], path: Path | str, code: str, message: str) -> None:
    issues.append(ValidationIssue(str(path), code, message))


def _schema_check(issues: list[ValidationIssue], root: Path, path: Path, schema: str, schema_dir: Path) -> Any:
    try:
        doc = load_yaml(path)
    except Exception as exc:
        _issue(issues, path.relative_to(root), "parse", str(exc))
        return None
    try:
        errors = validate_against_schema(doc, schema, schema_dir)
    except Exception as exc:
        _issue(issues, path.relative_to(root), "schema_loader", str(exc))
        return doc
    for error in errors:
        _issue(issues, path.relative_to(root), "schema", error)
    return doc


def _iter_signal_terms(signal: dict[str, Any]) -> Iterable[tuple[str, str]]:
    feedback = signal.get("feedback") or {}
    for item in feedback.get("signals") or []:
        term = item.get("term")
        if term:
            yield "feedback", term
    for rel in signal.get("relations") or []:
        for term in rel.get("dimensions") or []:
            yield "relation_dimension", term


def _check_rating_consistency(issues: list[ValidationIssue], path: str, rating: Any) -> None:
    if not isinstance(rating, dict):
        return
    score = rating.get("score")
    source = rating.get("source")
    confidence = rating.get("confidence")
    if score is None and (source != "none" or confidence != "none"):
        _issue(issues, path, "rating_consistency", "null score requires source=none and confidence=none")
    if score is not None and (source == "none" or confidence == "none"):
        _issue(issues, path, "rating_consistency", "non-null score requires non-none source and confidence")


def _similarity_endpoint_key(endpoint: Any) -> str | None:
    if not isinstance(endpoint, dict):
        return None
    if endpoint.get("kind") == "canonical" and isinstance(endpoint.get("work_id"), str):
        return f"work:{endpoint['work_id']}"
    if endpoint.get("kind") != "external":
        return None
    provider = endpoint.get("provider")
    if provider == "tmdb" and endpoint.get("media_type") in {"movie", "tv"} and isinstance(endpoint.get("id"), int):
        return f"external:tmdb:{endpoint['media_type']}:{endpoint['id']}"
    if provider == "imdb" and isinstance(endpoint.get("id"), str):
        return f"external:imdb:{endpoint['id']}"
    return None


def validate_repository(repo_root: Path) -> list[ValidationIssue]:
    root = Path(repo_root)
    media = root / "media"
    schema_dir = media / "schemas"
    issues: list[ValidationIssue] = []

    viewers_doc = _schema_check(issues, root, media / "config/viewers.yaml", "viewers.schema.json", schema_dir)
    groups_doc = _schema_check(issues, root, media / "config/groups.yaml", "groups.schema.json", schema_dir)
    vocabulary_doc = _schema_check(issues, root, media / "vocabulary.yaml", "vocabulary.schema.json", schema_dir)

    viewers = set((viewers_doc or {}).get("viewers", {})) if isinstance(viewers_doc, dict) else set()
    groups_map = (groups_doc or {}).get("groups", {}) if isinstance(groups_doc, dict) else {}
    groups = set(groups_map) if isinstance(groups_map, dict) else set()
    targets = viewers | groups

    for group_id, group in (groups_map.items() if isinstance(groups_map, dict) else []):
        for member in (group or {}).get("members", []):
            if member not in viewers:
                _issue(issues, "media/config/groups.yaml", "missing_viewer", f"group {group_id} references unknown viewer {member}")

    terms_map = (vocabulary_doc or {}).get("terms", {}) if isinstance(vocabulary_doc, dict) else {}
    terms = set(terms_map) if isinstance(terms_map, dict) else set()
    alias_to_term: dict[str, str] = {}
    for term_id, meta in (terms_map.items() if isinstance(terms_map, dict) else []):
        for alias in (meta or {}).get("aliases", []):
            alias_to_term.setdefault(alias, term_id)

    explicit_docs: list[tuple[Path, dict[str, Any]]] = []
    for path in iter_yaml_files(media / "preferences/explicit"):
        doc = _schema_check(issues, root, path, "explicit-preferences.schema.json", schema_dir)
        if isinstance(doc, dict):
            explicit_docs.append((path, doc))
            if doc.get("target") not in targets:
                _issue(issues, path.relative_to(root), "missing_target", f"unknown target {doc.get('target')}")

    works: dict[str, tuple[Path, dict[str, Any]]] = {}
    collections: dict[str, tuple[Path, dict[str, Any]]] = {}
    lists: dict[str, tuple[Path, dict[str, Any]]] = {}
    tombstones: dict[str, tuple[Path, dict[str, Any]]] = {}
    all_active: dict[str, str] = {}

    def add_entity(store: dict[str, tuple[Path, dict[str, Any]]], path: Path, doc: Any, kind: str) -> None:
        if not isinstance(doc, dict) or not isinstance(doc.get("id"), str):
            return
        entity_id = doc["id"]
        if entity_id in all_active:
            _issue(issues, path.relative_to(root), "duplicate_id", f"active id {entity_id} already used by {all_active[entity_id]}")
        else:
            all_active[entity_id] = kind
        if entity_id in store:
            _issue(issues, path.relative_to(root), "duplicate_id", f"duplicate {kind} id {entity_id}")
        store[entity_id] = (path, doc)

    for path in iter_yaml_files(media / "data/works"):
        add_entity(works, path, _schema_check(issues, root, path, "work.schema.json", schema_dir), "work")
    for path in iter_yaml_files(media / "data/collections"):
        add_entity(collections, path, _schema_check(issues, root, path, "collection.schema.json", schema_dir), "collection")
    for path in iter_yaml_files(media / "data/lists"):
        add_entity(lists, path, _schema_check(issues, root, path, "list.schema.json", schema_dir), "list")
    for path in iter_yaml_files(media / "data/tombstones"):
        doc = _schema_check(issues, root, path, "tombstone.schema.json", schema_dir)
        if isinstance(doc, dict) and isinstance(doc.get("id"), str):
            entity_id = doc["id"]
            if entity_id in tombstones:
                _issue(issues, path.relative_to(root), "duplicate_id", f"duplicate tombstone id {entity_id}")
            if entity_id in all_active:
                _issue(issues, path.relative_to(root), "duplicate_id", f"tombstone id {entity_id} collides with active entity")
            tombstones[entity_id] = (path, doc)

    work_ids = set(works)
    list_ids = set(lists)
    tombstone_ids = set(tombstones)

    pilot_path = media / "pilots/legacy-reassessment-primary.json"
    if pilot_path.exists():
        pilot_doc = _schema_check(issues, root, pilot_path, "reassessment-pilot.schema.json", schema_dir)
        if isinstance(pilot_doc, dict):
            for pilot_issue in validate_reassessment_snapshot(pilot_doc, canonical_work_ids=work_ids):
                _issue(issues, pilot_path.relative_to(root), pilot_issue.code, pilot_issue.message)

    imdb_seen: dict[str, str] = {}
    tmdb_seen: dict[tuple[str, int], str] = {}
    for work_id, (path, work) in works.items():
        identity = work.get("identity") or {}
        ext = identity.get("external_ids") or {}
        imdb = ext.get("imdb")
        if imdb:
            if imdb in imdb_seen:
                _issue(issues, path.relative_to(root), "duplicate_imdb", f"IMDb {imdb} already used by {imdb_seen[imdb]}")
            else:
                imdb_seen[imdb] = work_id
        tmdb = ext.get("tmdb")
        if isinstance(tmdb, dict) and tmdb.get("media_type") and tmdb.get("id") is not None:
            key = (tmdb["media_type"], tmdb["id"])
            if key in tmdb_seen:
                _issue(issues, path.relative_to(root), "duplicate_tmdb", f"TMDB {key} already used by {tmdb_seen[key]}")
            else:
                tmdb_seen[key] = work_id
            expected = "movie" if identity.get("format") == "movie" else "tv"
            if tmdb.get("media_type") != expected:
                _issue(issues, path.relative_to(root), "tmdb_media_type", f"format {identity.get('format')} requires TMDB media_type {expected}")

    def check_term(path_label: str, term: str) -> None:
        if term in terms:
            return
        if term in alias_to_term:
            _issue(issues, path_label, "vocabulary_alias", f"alias {term!r} used instead of canonical {alias_to_term[term]!r}")
        else:
            _issue(issues, path_label, "vocabulary_unknown", f"unknown vocabulary term {term!r}")

    def check_ref(path_label: str, ref: str, allowed: set[str], label: str = "work") -> None:
        if ref in tombstone_ids:
            _issue(issues, path_label, "stale_ref", f"reference {ref} points to tombstone; use active redirect target")
        elif ref not in allowed:
            _issue(issues, path_label, "missing_ref", f"unknown {label} reference {ref}")

    similarity_dir = media / "data" / "relations" / "similarity"
    for path in iter_yaml_files(similarity_dir):
        doc = _schema_check(issues, root, path, "work-similarity.schema.json", schema_dir)
        if not isinstance(doc, dict):
            continue
        path_label = str(path.relative_to(root))
        target = doc.get("target")
        if target not in targets:
            _issue(issues, path_label, "missing_target", f"unknown similarity target {target}")
        if isinstance(target, str) and path.stem != target:
            _issue(issues, path_label, "similarity_filename", f"similarity target {target} must be stored in {target}.yaml")
        seen_pairs: set[tuple[str, str]] = set()
        for index, relation in enumerate(doc.get("relations") or []):
            if not isinstance(relation, dict):
                continue
            relation_path = f"{path_label}:relations[{index}]"
            left = relation.get("left")
            right = relation.get("right")
            for endpoint in (left, right):
                if isinstance(endpoint, dict) and endpoint.get("kind") == "canonical" and isinstance(endpoint.get("work_id"), str):
                    check_ref(relation_path, endpoint["work_id"], work_ids)
            for term in relation.get("terms") or []:
                if isinstance(term, str):
                    check_term(relation_path, term)
            left_key = _similarity_endpoint_key(left)
            right_key = _similarity_endpoint_key(right)
            if left_key is None or right_key is None:
                continue
            if left_key == right_key:
                _issue(issues, relation_path, "self_relation", "similarity relation points to the same endpoint")
            pair = tuple(sorted((left_key, right_key)))
            if pair in seen_pairs:
                _issue(issues, relation_path, "duplicate_similarity", f"duplicate similarity pair {pair[0]} <-> {pair[1]}")
            else:
                seen_pairs.add(pair)
            if left_key > right_key:
                _issue(issues, relation_path, "similarity_order", "similarity endpoints must be stored in canonical lexical order")

    def check_signal_map(work_id: str, path: Path, mapping: Any, expected_targets: set[str]) -> None:
        if not isinstance(mapping, dict):
            return
        for target, signal in mapping.items():
            if target not in expected_targets:
                _issue(issues, path.relative_to(root), "missing_target", f"unknown signal target {target}")
            if not isinstance(signal, dict):
                continue
            _check_rating_consistency(issues, str(path.relative_to(root)), signal.get("rating"))
            for _, term in _iter_signal_terms(signal):
                check_term(str(path.relative_to(root)), term)
            for relation in signal.get("relations") or []:
                target_id = relation.get("target_id")
                if target_id == work_id:
                    _issue(issues, path.relative_to(root), "self_relation", f"{relation.get('type')} points to self")
                elif target_id:
                    check_ref(str(path.relative_to(root)), target_id, work_ids)

    for work_id, (path, work) in works.items():
        check_signal_map(work_id, path, work.get("viewer_signals"), viewers)
        check_signal_map(work_id, path, work.get("group_signals"), groups)
        for target in (work.get("target_states") or {}):
            if target not in targets:
                _issue(issues, path.relative_to(root), "missing_target", f"unknown target state {target}")
        metadata = work.get("metadata") or {}
        external = metadata.get("external") or {}
        for term in external.get("genres") or []:
            check_term(str(path.relative_to(root)), term)
        for term in external.get("content_warnings") or []:
            check_term(str(path.relative_to(root)), term)
        for trait in (metadata.get("semantic") or {}).get("traits") or []:
            if trait.get("term"):
                check_term(str(path.relative_to(root)), trait["term"])
        nums: set[int] = set()
        for season in work.get("seasons") or []:
            number = season.get("number")
            if number in nums:
                _issue(issues, path.relative_to(root), "duplicate_season", f"duplicate season number {number}")
            else:
                nums.add(number)
            for trait in (((season.get("metadata") or {}).get("semantic") or {}).get("traits") or []):
                if trait.get("term"):
                    check_term(str(path.relative_to(root)), trait["term"])
            check_signal_map(work_id, path, season.get("viewer_signals"), viewers)
            check_signal_map(work_id, path, season.get("group_signals"), groups)
        for relation in work.get("canonical_relations") or []:
            target_id = relation.get("target_id")
            if target_id == work_id:
                _issue(issues, path.relative_to(root), "self_relation", f"canonical {relation.get('type')} points to self")
            elif target_id:
                check_ref(str(path.relative_to(root)), target_id, work_ids)

    for collection_id, (path, collection) in collections.items():
        check_signal_map(collection_id, path, collection.get("viewer_signals"), viewers)
        check_signal_map(collection_id, path, collection.get("group_signals"), groups)
        for target in (collection.get("target_states") or {}):
            if target not in targets:
                _issue(issues, path.relative_to(root), "missing_target", f"unknown target state {target}")
        for member in collection.get("member_ids") or []:
            check_ref(str(path.relative_to(root)), member, work_ids)

    for _, (path, list_doc) in lists.items():
        if list_doc.get("target") not in targets:
            _issue(issues, path.relative_to(root), "missing_target", f"unknown list target {list_doc.get('target')}")
        for member in list_doc.get("member_ids") or []:
            check_ref(str(path.relative_to(root)), member, work_ids)

    for path, doc in explicit_docs:
        for bucket in ("preferences", "rules", "constraints"):
            for entry in doc.get(bucket) or []:
                if entry.get("term"):
                    check_term(str(path.relative_to(root)), entry["term"])

    redirects = {tid: doc.get("redirect_to") for tid, (_, doc) in tombstones.items()}
    for tid, target in redirects.items():
        path = tombstones[tid][0].relative_to(root)
        if tid == target:
            _issue(issues, path, "self_redirect", f"tombstone {tid} redirects to itself")
            continue
        seen: set[str] = set()
        cur = tid
        while cur in redirects:
            if cur in seen:
                _issue(issues, path, "redirect_cycle", f"redirect cycle involving {cur}")
                break
            seen.add(cur)
            cur = redirects[cur]
        else:
            if cur not in all_active:
                _issue(issues, path, "missing_ref", f"redirect target {cur} does not resolve to active entity")

    event_ids: set[str] = set()
    interactions_dir = media / "data/interactions"
    if interactions_dir.exists():
        for path in sorted(interactions_dir.glob("*.jsonl")):
            stem = path.stem
            valid_name = len(stem) == 7 and stem[4] == "-" and stem[:4].isdigit() and stem[5:].isdigit()
            if not valid_name:
                _issue(issues, path.relative_to(root), "interaction_filename", "interaction file must be YYYY-MM.jsonl")
            try:
                rows = list(iter_jsonl(path))
            except Exception as exc:
                _issue(issues, path.relative_to(root), "parse", str(exc))
                continue
            for line_no, event in rows:
                p = f"{path.relative_to(root)}:{line_no}"
                for error in validate_against_schema(event, "interaction.schema.json", schema_dir):
                    _issue(issues, p, "schema", error)
                event_id = event.get("id")
                if event_id in event_ids:
                    _issue(issues, p, "duplicate_interaction", f"duplicate event id {event_id}")
                elif event_id:
                    event_ids.add(event_id)
                timestamp = event.get("at")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                        if valid_name and f"{dt.year:04d}-{dt.month:02d}" != stem:
                            _issue(issues, p, "interaction_month", f"timestamp month does not match {stem}")
                    except ValueError:
                        _issue(issues, p, "interaction_timestamp", f"invalid timestamp {timestamp}")
                if event.get("target") not in targets:
                    _issue(issues, p, "missing_target", f"unknown interaction target {event.get('target')}")
                if event.get("work_id"):
                    check_ref(p, event["work_id"], work_ids)
                if event.get("list_id"):
                    if event["list_id"] in tombstone_ids:
                        _issue(issues, p, "stale_ref", f"list reference {event['list_id']} is tombstoned")
                    elif event["list_id"] not in list_ids:
                        _issue(issues, p, "missing_ref", f"unknown list reference {event['list_id']}")

    return sorted(set(issues))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate canonical media v4 repository data")
    parser.add_argument("repo_root", nargs="?", default=".")
    args = parser.parse_args(argv)
    issues = validate_repository(Path(args.repo_root))
    for issue in issues:
        print(f"{issue.path}: [{issue.code}] {issue.message}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
